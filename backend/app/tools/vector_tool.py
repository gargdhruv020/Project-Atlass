"""
Vector Search Tool
Retrieves relevant unstructured text chunks from local ChromaDB.
"""

from typing import List, Dict, Any
from app.retrieval.vector_store import vector_store

class VectorTool:
    @staticmethod
    def search_unstructured_content(query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Query ChromaDB for relevant narrative insights."""
        try:
            results = vector_store.query_similar(query=query, n_results=n_results)
            return [
                {
                    "content": r["content"],
                    "source": r["metadata"].get("source", "unknown"),
                    "chunk_id": r["metadata"].get("chunk_id", 0),
                    "source_type": "vector_retrieval"
                }
                for r in results
            ]
        except Exception:
            # Fallback if no collection indexed yet
            return []
