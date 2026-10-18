"""
Embedding Provider for Project Atlas
Unified vector embedding provider supporting Hugging Face (local ONNX all-MiniLM-L6-v2 or API)
and Local Ollama embeddings with automatic resilient fallback.
"""

from typing import List, Optional, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from chromadb.api.types import Documents, Embeddings
from app.core.config import settings
from app.observability.logger import logger


class AtlasEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """
    Unified embedding function for Project Atlas supporting Hugging Face models
    (local ONNX all-MiniLM-L6-v2 or HuggingFace API) and Local Ollama embeddings.
    Provides automatic resilient fallback so vector search remains reliable across environments.
    """
    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.provider = (provider or getattr(settings, "EMBEDDING_PROVIDER", "huggingface")).lower()
        self.base_url = base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        self.api_key = api_key or getattr(settings, "HUGGINGFACE_API_KEY", None)

        if self.provider == "ollama":
            self.model_name = model_name or getattr(settings, "OLLAMA_MODEL", "nomic-embed-text")
        else:
            self.model_name = model_name or getattr(settings, "HUGGINGFACE_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")

        # Local Hugging Face ONNX default model (all-MiniLM-L6-v2)
        self._fallback_ef = embedding_functions.DefaultEmbeddingFunction()
        self._primary_ef: Optional[embedding_functions.EmbeddingFunction] = None
        self._active_provider = self.provider
        self._status = "ready"

        self._init_primary()

    def _init_primary(self):
        """Initializes primary embedding provider according to configuration."""
        if self.provider == "ollama":
            try:
                self._primary_ef = embedding_functions.OllamaEmbeddingFunction(
                    url=self.base_url,
                    model_name=self.model_name
                )
                self._active_provider = "ollama"
            except Exception as e:
                logger.warning(
                    f"Ollama embedding initialization deferred ({e}). "
                    f"Falling back to local Hugging Face ONNX model ({self.model_name})."
                )
                self._primary_ef = None
                self._active_provider = "huggingface-local-fallback"
        elif self.provider == "huggingface":
            if self.api_key:
                try:
                    self._primary_ef = embedding_functions.HuggingFaceEmbeddingFunction(
                        api_key=self.api_key,
                        model_name=self.model_name
                    )
                    self._active_provider = "huggingface-api"
                except Exception as e:
                    logger.warning(
                        f"Hugging Face API initialization deferred ({e}). "
                        f"Falling back to local Hugging Face ONNX model."
                    )
                    self._primary_ef = None
                    self._active_provider = "huggingface-local"
            else:
                # Default local ONNX embedding (all-MiniLM-L6-v2)
                self._primary_ef = self._fallback_ef
                self._active_provider = "huggingface-local"
        else:
            logger.warning(f"Unrecognized embedding provider '{self.provider}'. Using local Hugging Face model.")
            self._primary_ef = self._fallback_ef
            self._active_provider = "huggingface-local"

    @staticmethod
    def name() -> str:
        """Name of the embedding function."""
        return "atlas-embedding-function"

    def get_config(self) -> Dict[str, Any]:
        """Configuration dictionary for ChromaDB serialization."""
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "base_url": self.base_url
        }

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "AtlasEmbeddingFunction":
        """Instantiates embedding function from ChromaDB config dictionary."""
        return AtlasEmbeddingFunction(
            provider=config.get("provider"),
            model_name=config.get("model_name"),
            base_url=config.get("base_url")
        )

    def get_health_info(self) -> Dict[str, Any]:
        """Returns diagnostic health info for /health endpoint."""
        return {
            "status": self._status,
            "provider": self.provider,
            "active_provider": self._active_provider,
            "model": self.model_name
        }

    def __call__(self, input: Documents) -> Embeddings:
        """Generate vector embeddings for input documents."""
        if self._primary_ef is not None:
            try:
                return self._primary_ef(input)
            except Exception as e:
                logger.warning(
                    f"Primary embedding call ({self.provider}) failed ({e}). "
                    f"Falling back to local Hugging Face ONNX embedding."
                )
                self._active_provider = "huggingface-local-fallback"

        # Fallback to local Hugging Face ONNX model
        return self._fallback_ef(input)


class LocalOllamaEmbeddingFunction(AtlasEmbeddingFunction):
    """Backward compatibility wrapper for Ollama embeddings."""
    def __init__(self, base_url: str = None, model_name: str = None):
        super().__init__(
            provider="ollama",
            model_name=model_name or getattr(settings, "OLLAMA_MODEL", "nomic-embed-text"),
            base_url=base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        )


# Singleton instances
atlas_embedding_function = AtlasEmbeddingFunction()
ollama_embedding_function = atlas_embedding_function  # Backward compatibility alias
