"""
ChromaDB Vector Store Manager
Manages local persistent vector storage for unstructured market research reports.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.ingestion.document_parser import DocumentChunk

class ChromaStore:
    def __init__(self, persist_dir: Optional[str] = None, collection_name: Optional[str] = None):
        self.persist_dir = Path(persist_dir or settings.CHROMA_PERSIST_DIRECTORY)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self._client = None
        self._collection = None

    def _get_client(self):
        """Lazy load chromadb client."""
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        return self._client

    def get_collection(self):
        """Retrieve or create collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(name=self.collection_name)
        return self._collection

    def add_documents(self, chunks: List[DocumentChunk]):
        """Add document chunks to ChromaDB collection."""
        collection = self.get_collection()
        ids = [f"{c.metadata.get('source', 'doc')}_{c.metadata.get('chunk_id', i)}" for i, c in enumerate(chunks)]
        documents = [c.content for c in chunks]
        metadatas = [c.metadata for c in chunks]
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def query_similar(self, query: str, n_results: int = 4) -> List[Dict[str, Any]]:
        """Semantic search query in collection."""
        collection = self.get_collection()
        results = collection.query(query_texts=[query], n_results=n_results)
        
        output = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(docs)
            distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)
            for doc, meta, dist in zip(docs, metas, distances):
                output.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": dist
                })
        return output

# Singleton instance
vector_store = ChromaStore()
