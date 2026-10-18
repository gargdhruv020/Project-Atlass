"""
Startup Ingestion Script for Project Atlas Docker Container
Ensures report ingestion runs only once when collection is empty,
preventing duplicate chunk generation and redundant embedding costs on container restarts.
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.observability.logger import logger
from app.retrieval.vector_store import vector_store
from app.ingestion.pipeline import ReportIngestionPipeline
from app.core.config import settings


def run_startup_ingest():
    """Checks ChromaDB collection count; ingests sample documents if empty."""
    try:
        collection = vector_store.get_collection()
        count = collection.count()
        if count > 0:
            logger.info(
                f"[StartupIngest] ChromaDB collection '{vector_store.collection_name}' already contains {count} chunks. "
                "Skipping repeated ingestion to maintain stability."
            )
            return

        logger.info(
            f"[StartupIngest] ChromaDB collection is empty (0 chunks). "
            "Executing initial idempotent ingestion of sample reports..."
        )
        sample_reports_dir = Path(settings.DOCUMENTS_DIR) / "sample_reports"
        if not sample_reports_dir.exists():
            sample_reports_dir = Path("/app/documents/sample_reports")

        if sample_reports_dir.exists():
            pipeline = ReportIngestionPipeline()
            summary = pipeline.ingest_directory(sample_reports_dir)
            logger.info(
                f"[StartupIngest] Initial ingestion successful: {summary.successful_files} files, "
                f"{summary.total_chunks} total chunks indexed into ChromaDB."
            )
        else:
            logger.warning(f"[StartupIngest] Documents directory not found at '{sample_reports_dir}'. Skipping ingestion.")
    except Exception as e:
        logger.error(f"[StartupIngest] Startup ingestion notice: {e}")


if __name__ == "__main__":
    run_startup_ingest()
