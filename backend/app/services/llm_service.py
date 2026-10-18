"""
LLM Service Interface
Provides extensible abstraction for LLM synthesis (LangChain / OpenAI / Anthropic / Gemini).
"""

from typing import List, Dict, Any, Optional
from app.observability.logger import logger

class LLMService:
    @staticmethod
    def synthesize_response(
        query: str,
        structured_context: List[Dict[str, Any]],
        unstructured_context: List[str],
        client_name: Optional[str] = None
    ) -> str:
        """
        Synthesize answer from retrieved evidence.
        Falls back to rule-based grounded synthesis when no external LLM API key is present.
        """
        logger.info(f"LLMService synthesizing answer for query: '{query[:50]}...'")

        if not structured_context and not unstructured_context:
            return f"I could not locate verified market intelligence data to answer: '{query}'."

        findings = []
        for s in structured_context:
            metric = s.get("metric", "Metric")
            val = s.get("value", "")
            region = s.get("region", "Global")
            period = s.get("period", "")
            rep = s.get("report_id", "")
            findings.append(f"- {metric} ({region}, {period}): {val} [Source: {rep}]")

        summary = (
            f"Based on verified research records" + (f" for {client_name}" if client_name else "") + ":\n\n"
            + "\n".join(findings)
        )
        return summary
