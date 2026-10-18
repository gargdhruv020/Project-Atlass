"""
Report Ingestion Pipeline
Coordinates multi-format document extraction, metadata validation, chunking,
and ingestion reporting.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from app.ingestion.document_parser import DocumentParser, DocumentChunker, DocumentChunk
from app.retrieval.vector_store import vector_store
from app.observability.logger import logger

class IngestionSummary:
    def __init__(self):
        self.total_reports_discovered: int = 0
        self.total_reports_processed: int = 0
        self.total_chunks_created: int = 0
        self.processed_reports: List[Dict[str, Any]] = []
        self.missing_metadata_warnings: List[Dict[str, Any]] = []
        self.extraction_errors: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_reports_discovered": self.total_reports_discovered,
            "total_reports_processed": self.total_reports_processed,
            "total_chunks_created": self.total_chunks_created,
            "processed_reports": self.processed_reports,
            "missing_metadata_warnings": self.missing_metadata_warnings,
            "extraction_errors": self.extraction_errors
        }

class ReportIngestionPipeline:
    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 40):
        self.chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def scan_directory(self, documents_dir: Path) -> List[Path]:
        """Finds all supported document files (.pdf, .html, .htm, .md, .txt)."""
        supported_extensions = {".pdf", ".html", ".htm", ".md", ".txt"}
        files = []
        for p in documents_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in supported_extensions:
                files.append(p)
        return sorted(files)

    def process_document(self, file_path: Path) -> Tuple[List[DocumentChunk], Dict[str, Any], List[str]]:
        """
        Parses and chunks a single document.
        Does NOT alter or write to vector storage (separation of processing from storage).
        """
        pages, metadata, missing_fields = DocumentParser.parse_file(file_path)
        chunks = self.chunker.chunk_pages(pages, metadata)
        return chunks, metadata, missing_fields

    def execute_pipeline(
        self,
        documents_dir: Path,
        load_to_chroma: bool = True
    ) -> IngestionSummary:
        """
        Runs the full ingestion pipeline across all discovered documents.
        Validates metadata, creates stable chunks, and optionally syncs to ChromaDB.
        """
        summary = IngestionSummary()
        files = self.scan_directory(documents_dir)
        summary.total_reports_discovered = len(files)
        logger.info(f"Ingestion Pipeline discovered {len(files)} document file(s) in {documents_dir}")

        all_chunks: List[DocumentChunk] = []

        for f in files:
            try:
                chunks, metadata, missing_fields = self.process_document(f)
                summary.total_reports_processed += 1
                summary.total_chunks_created += len(chunks)

                report_info = {
                    "file_name": f.name,
                    "report_id": metadata.get("report_id", "UNKNOWN"),
                    "title": metadata.get("title", ""),
                    "chunks_count": len(chunks),
                    "sector": metadata.get("sector", ""),
                    "region": metadata.get("region", ""),
                    "year": metadata.get("year", "")
                }
                summary.processed_reports.append(report_info)

                if missing_fields:
                    summary.missing_metadata_warnings.append({
                        "file_name": f.name,
                        "report_id": metadata.get("report_id", "UNKNOWN"),
                        "missing_fields": missing_fields
                    })

                all_chunks.extend(chunks)

            except Exception as e:
                logger.error(f"Failed to process document {f.name}: {e}")
                summary.extraction_errors.append({
                    "file_name": f.name,
                    "error": str(e)
                })

        # Load to local ChromaDB if requested
        if load_to_chroma and all_chunks:
            logger.info(f"Syncing {len(all_chunks)} chunks to local persistent ChromaDB...")
            vector_store.add_documents(all_chunks)
            logger.info("ChromaDB sync complete.")

        return summary

    # Backward compatibility alias
    ingest_directory = execute_pipeline
