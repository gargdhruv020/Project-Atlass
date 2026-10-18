"""
Ingestion Endpoint: POST /ingest
Parses and stores research reports in local persistent ChromaDB.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.security.auth import require_api_key
from app.schemas.ingest import IngestRequest, IngestResponse
from app.services.ingestion_service import IngestionService
from app.observability.logger import logger

router = APIRouter(tags=["Ingestion"])

@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest market research report into ChromaDB",
    description="Loads, chunks, and persists report content or local file into ChromaDB vector store."
)
async def ingest_endpoint(
    ingest_req: IngestRequest,
    api_key: str = Depends(require_api_key)
):
    """
    Ingests report text or document file into local persistent vector collection.
    Requires valid API authentication.
    """
    logger.info(f"Ingestion requested for report: {ingest_req.report_id}")

    try:
        result = IngestionService.ingest_report_document(
            report_id=ingest_req.report_id,
            title=ingest_req.title,
            content=ingest_req.content,
            file_path=ingest_req.file_path,
            metadata=ingest_req.metadata
        )
        return IngestResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failure: {str(e)}"
        )
