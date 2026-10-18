"""
ChromaDB Vector Store Service for Project Atlas
Exclusively manages local persistent vector storage using ChromaDB and Local Ollama embeddings.
Enforces client purchase entitlement verification against MySQL before surfacing retrieved text.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.api.models.Collection import Collection
from sqlalchemy.orm import Session

from app.core.config import settings
from app.retrieval.embedding_provider import atlas_embedding_function, ollama_embedding_function
from app.observability.logger import logger

class VectorStoreService:
    """
    Reusable vector store service providing local ChromaDB persistent collection management,
    idempotent chunk upserts, semantic similarity search, metadata filtering, and entitlement enforcement.
    """
    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        self.persist_dir = Path(persist_dir or settings.CHROMA_PERSIST_DIRECTORY)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.embedding_function = atlas_embedding_function
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection: Optional[Collection] = None

    def get_client(self) -> chromadb.PersistentClient:
        """Lazy load persistent ChromaDB client."""
        if self._client is None:
            logger.info(f"Connecting to persistent ChromaDB at '{self.persist_dir.resolve()}'")
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        return self._client

    def get_collection(self) -> Collection:
        """Retrieve or create persistent ChromaDB collection with configured embedding function."""
        if self._collection is None:
            client = self.get_client()
            try:
                self._collection = client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
            except ValueError as e:
                if "Embedding function conflict" in str(e):
                    logger.warning("Embedding function conflict on existing collection. Resetting collection.")
                    client.delete_collection(name=self.collection_name)
                    self._collection = client.get_or_create_collection(
                        name=self.collection_name,
                        embedding_function=self.embedding_function,
                        metadata={"hnsw:space": "cosine"}
                    )
                else:
                    raise
            logger.info(f"ChromaDB collection '{self.collection_name}' initialized with {self._collection.count()} chunks")
        return self._collection

    def add_or_update_chunks(self, chunks: List[Any]) -> int:
        """
        Idempotently adds or updates chunks using stable chunk IDs.
        Stores chunk text, embeddings (generated via Ollama), and required metadata fields:
        report_id, sector, region, year, page.
        """
        if not chunks:
            return 0

        collection = self.get_collection()
        ids = []
        documents = []
        metadatas = []

        for i, c in enumerate(chunks):
            # 1. Chunk ID (stable identifier)
            chunk_id = getattr(c, "chunk_id", None)
            if not chunk_id:
                chunk_id = f"{c.metadata.get('report_id', 'DOC')}_chunk_{i}"

            ids.append(chunk_id)
            documents.append(c.content)

            # 2. Required Metadata Fields
            raw_meta = getattr(c, "metadata", {}) or {}
            clean_meta = {
                "report_id": str(raw_meta.get("report_id", "UNKNOWN")),
                "sector": str(raw_meta.get("sector", "Unspecified")),
                "region": str(raw_meta.get("region", "Global")),
                "year": str(raw_meta.get("year", "2025")),
                "page": int(raw_meta.get("page", 1)),
                "title": str(raw_meta.get("title", "")),
                "is_synthetic": bool(raw_meta.get("is_synthetic", False))
            }
            metadatas.append(clean_meta)

        # Upsert ensures repeated ingestion updates existing entries without creating duplicates
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"Upserted {len(ids)} chunk(s) into ChromaDB collection '{self.collection_name}'")
        return len(ids)

    # Aliases for backward compatibility
    add_documents = add_or_update_chunks

    def similarity_search(
        self,
        query: str,
        n_results: int = 4,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic similarity search with optional metadata filtering.
        """
        collection = self.get_collection()
        kwargs = {
            "query_texts": [query],
            "n_results": n_results
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)
        return self._format_query_results(results)

    def entitled_similarity_search(
        self,
        db: Session,
        client_id: str,
        query: str,
        n_results: int = 4,
        report_id: Optional[str] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Security Enforcement Boundary:
        Retrieves vector chunks only after independently verifying client entitlements against MySQL.
        A client never receives content from an unpurchased paid report.
        """
        from app.services.client_service import ClientService
        from app.models.report import Report

        # 1. Fetch client entitlements from MySQL
        client = ClientService.get_client(db, client_id)
        if not client:
            logger.warning(f"Entitled search rejected: client '{client_id}' not found in MySQL.")
            return []

        purchased_reports = [r.strip() for r in (client.purchased_reports or "").split(",") if r.strip()]
        
        # Public reports are accessible to all clients
        public_reports = [r.id for r in db.query(Report).filter(Report.access == "public").all()]
        allowed_reports = set(purchased_reports + public_reports)

        if report_id:
            allowed_reports = allowed_reports.intersection({report_id})

        if not allowed_reports:
            logger.info(f"Client '{client_id}' has zero entitled reports for query scope.")
            return []

        # 2. ChromaDB metadata filter layer
        where_filter = None
        if len(allowed_reports) == 1:
            where_filter = {"report_id": list(allowed_reports)[0]}
        elif len(allowed_reports) > 1:
            where_filter = {"report_id": {"$in": sorted(list(allowed_reports))}}

        raw_candidates = self.similarity_search(query=query, n_results=n_results, where=where_filter)

        # 3. Independent second-layer verification against MySQL and similarity threshold check
        verified_results = []
        for item in raw_candidates:
            item_report_id = item["metadata"].get("report_id")
            has_access, reason = ClientService.check_report_access(db, client_id, item_report_id)
            if not has_access:
                logger.error(
                    f"SECURITY ALERT: Blocked unentitled chunk from report '{item_report_id}' "
                    f"for client '{client_id}' despite vector search match."
                )
                continue

            # Check similarity threshold if specified
            if similarity_threshold is not None:
                dist = item.get("distance", 0.0)
                if dist > similarity_threshold:
                    logger.debug(
                        f"Chunk {item.get('chunk_id')} filtered out by similarity threshold "
                        f"({dist:.4f} > {similarity_threshold:.4f})"
                    )
                    continue

            verified_results.append(item)

        return verified_results

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single chunk by stable ID."""
        collection = self.get_collection()
        res = collection.get(ids=[chunk_id])
        if res and res.get("ids"):
            return {
                "chunk_id": res["ids"][0],
                "content": res["documents"][0],
                "metadata": res["metadatas"][0] if res["metadatas"] else {}
            }
        return None

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """Retrieve all stored chunks."""
        collection = self.get_collection()
        res = collection.get()
        chunks = []
        if res and res.get("ids"):
            for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
                chunks.append({
                    "chunk_id": cid,
                    "content": doc,
                    "metadata": meta
                })
        return chunks

    def count(self) -> int:
        """Returns total number of chunks currently persisted in the collection."""
        return self.get_collection().count()

    def get_health_status(self) -> Dict[str, Any]:
        """Check vector store health and persistence availability."""
        try:
            total_count = self.count()
            emb_info = {}
            if hasattr(self.embedding_function, "get_health_info"):
                emb_info = self.embedding_function.get_health_info()
            else:
                emb_info = {
                    "provider": getattr(settings, "EMBEDDING_PROVIDER", "huggingface"),
                    "model": getattr(settings, "HUGGINGFACE_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"),
                    "status": "ready"
                }
            provider = emb_info.get("provider", "huggingface")
            model = emb_info.get("model", "sentence-transformers/all-MiniLM-L6-v2")
            if "huggingface" in provider.lower():
                emb_model_display = f"Hugging Face ({model}) with Ollama compatibility"
            else:
                emb_model_display = f"Ollama ({model})"

            return {
                "status": "available",
                "collection": self.collection_name,
                "persist_directory": str(self.persist_dir.resolve()),
                "total_chunks": total_count,
                "embedding_provider": provider,
                "embedding_model": emb_model_display,
                "embedding_model_name": model,
                "embedding_status": emb_info.get("status", "ready")
            }
        except Exception as e:
            return {
                "status": f"unhealthy: {type(e).__name__}",
                "error": str(e)
            }

    def _format_query_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Helper to format Chroma query results."""
        output = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            ids = results["ids"][0] if "ids" in results and results["ids"] else [""] * len(docs)
            metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(docs)
            distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)
            for cid, doc, meta, dist in zip(ids, docs, metas, distances):
                output.append({
                    "chunk_id": cid,
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                    "source_type": "vector_retrieval"
                })
        return output

# Singleton service instances
vector_store_service = VectorStoreService()
vector_store = vector_store_service  # Alias for backward compatibility
