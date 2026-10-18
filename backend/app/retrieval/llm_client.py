"""
LLM Client Interface for Project Atlas
Supports local Ollama and OpenAI-compatible API providers with defensive error handling,
timeout enforcement, and graceful fallback to deterministic grounded synthesis.
"""

import json
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.observability.logger import logger


class LLMClient:
    """Client for querying the configured LLM API (Ollama or OpenAI-compatible)."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        self.model = model or settings.LLM_MODEL
        self.api_base = (api_base or settings.LLM_API_BASE).rstrip("/")
        self.api_key = api_key or settings.LLM_API_KEY
        self.timeout = timeout or float(settings.REQUEST_TIMEOUT_SECONDS)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """
        Sends generation request to the configured LLM.
        Returns the generated response string, or None if the LLM is offline/errored.
        """
        if self.provider == "mock":
            logger.info("LLM provider set to 'mock'; skipping external LLM call.")
            return None

        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE

        try:
            if self.provider == "ollama":
                return self._call_ollama(system_prompt, user_prompt, temp)
            elif self.provider in ("openai", "openai-compatible"):
                return self._call_openai(system_prompt, user_prompt, temp)
            else:
                logger.warning(f"Unrecognized LLM provider '{self.provider}'. Falling back to grounded synthesis.")
                return None
        except httpx.ConnectError:
            logger.warning(
                f"LLM daemon at {self.api_base} is offline or unreachable. "
                f"Employing deterministic grounded synthesis fallback."
            )
            return None
        except httpx.TimeoutException:
            logger.warning(
                f"LLM request timed out after {self.timeout}s. "
                f"Employing deterministic grounded synthesis fallback."
            )
            return None
        except Exception as e:
            logger.warning(
                f"LLM generation failed ({type(e).__name__}: {e}). "
                f"Employing deterministic grounded synthesis fallback."
            )
            return None

    def _call_ollama(self, system_prompt: str, user_prompt: str, temperature: float) -> Optional[str]:
        """Calls local Ollama REST API (/api/generate)."""
        url = f"{self.api_base}/api/generate"
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("response", "").strip()
                if content:
                    return content
            logger.warning(f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}")
            return None

    def _call_openai(self, system_prompt: str, user_prompt: str, temperature: float) -> Optional[str]:
        """Calls OpenAI-compatible /v1/chat/completions endpoint."""
        url = f"{self.api_base}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "").strip()
            logger.warning(f"OpenAI endpoint returned HTTP {resp.status_code}: {resp.text[:200]}")
            return None

    def is_available(self) -> bool:
        """Checks if the LLM endpoint is actively reachable."""
        if self.provider == "mock":
            return False
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(self.api_base)
                return resp.status_code < 500
        except Exception:
            return False


# Singleton client
llm_client = LLMClient()
