"""
Embedding Provider for Project Atlas
Configures Local Ollama embedding model with automatic resilient fallback.
"""

from typing import List, Optional, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from chromadb.api.types import Documents, Embeddings
from app.core.config import settings
from app.observability.logger import logger

class LocalOllamaEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """
    Embedding function integrating with local Ollama service (e.g. nomic-embed-text).
    Falls back gracefully to local onnx embeddings if the Ollama daemon is offline,
    ensuring continuous service availability during tests and local setup.
    """
    def __init__(self, base_url: str = None, model_name: str = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model_name = model_name or settings.OLLAMA_MODEL
        self._fallback_ef = embedding_functions.DefaultEmbeddingFunction()
        self._ollama_ef: Optional[embedding_functions.OllamaEmbeddingFunction] = None
        self._using_ollama = True

        try:
            self._ollama_ef = embedding_functions.OllamaEmbeddingFunction(
                url=self.base_url,
                model_name=self.model_name
            )
        except Exception as e:
            logger.warning(
                f"Ollama embedding function initialization deferred ({e}). "
                f"Local fallback embedding model active."
            )
            self._using_ollama = False

    def name(self) -> str:
        """Name of the embedding function."""
        return f"ollama-{self.model_name}"

    def get_config(self) -> Dict[str, Any]:
        """Configuration dictionary for ChromaDB serialization."""
        return {
            "base_url": self.base_url,
            "model_name": self.model_name
        }

    def __call__(self, input: Documents) -> Embeddings:
        """Generate vector embeddings for input documents."""
        if self._using_ollama and self._ollama_ef is not None:
            try:
                return self._ollama_ef(input)
            except Exception as e:
                logger.warning(
                    f"Local Ollama embedding failed at {self.base_url} ({e}). "
                    f"Falling back to local embedded model."
                )
                self._using_ollama = False

        # Fallback to local embedding
        return self._fallback_ef(input)

# Default provider instance
ollama_embedding_function = LocalOllamaEmbeddingFunction()
