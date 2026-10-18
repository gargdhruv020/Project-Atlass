"""
Report Ingestion Service
Orchestrates document parsing and local ChromaDB persistence.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from app.core.config import settings
from app.ingestion.document_parser import DocumentParser, DocumentChunk
from app.retrieval.vector_store import vector_store
from app.observability.logger import logger

class IngestionService:
    @staticmethod
    def ingest_report_document(
        report_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parses and stores document chunks into local persistent ChromaDB.
        """
        meta = metadata.copy() if metadata else {}
        meta["report_id"] = report_id
        if title:
            meta["title"] = title

        parser = DocumentParser(chunk_size=400, chunk_overlap=40)
        chunks = []

        if content and content.strip():
            logger.info(f"Ingesting raw text content for report '{report_id}'")
            chunks = parser.chunk_text(
                content,
                metadata={"source": f"report_{report_id}", **meta}
            )
        elif file_path:
            target_path = Path(file_path)
            if not target_path.is_absolute():
                target_path = Path(settings.DOCUMENTS_DIR) / file_path
            
            if not target_path.exists():
                raise FileNotFoundError(f"Document file not found at: {target_path}")
            
            logger.info(f"Ingesting file '{target_path.name}' for report '{report_id}'")
            chunks = parser.parse_text_file(target_path)
            for c in chunks:
                c.metadata.update(meta)
        else:
            raise ValueError("Either 'content' or 'file_path' must be provided for ingestion.")

        if not chunks:
            raise ValueError("Document yielded no text chunks for ingestion.")

        # Persist to local ChromaDB
        vector_store.add_documents(chunks)
        logger.info(f"Successfully ingested {len(chunks)} chunks into ChromaDB for report '{report_id}'")

        return {
            "status": "success",
            "report_id": report_id,
            "chunks_ingested": len(chunks),
            "collection": vector_store.collection_name,
            "message": f"Successfully ingested {len(chunks)} chunks for report '{report_id}' into ChromaDB"
        }
