"""
Vector Search Tool
Retrieves relevant unstructured text chunks from local ChromaDB exclusively.
"""

from typing import List, Dict, Any, Optional
from app.retrieval.vector_store import vector_store_service

class VectorTool:
    @staticmethod
    def search_unstructured_content(
        query: str,
        n_results: int = 3,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Query ChromaDB for relevant narrative insights."""
        try:
            results = vector_store_service.similarity_search(query=query, n_results=n_results, where=where)
            return [
                {
                    "content": r["content"],
                    "source": r["metadata"].get("report_id", "unknown"),
                    "chunk_id": r.get("chunk_id", ""),
                    "page": r["metadata"].get("page", 1),
                    "sector": r["metadata"].get("sector", ""),
                    "metadata": r.get("metadata", {}),
                    "source_type": "vector_retrieval"
                }
                for r in results
            ]
        except Exception:
            return []
