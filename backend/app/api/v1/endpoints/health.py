"""
Health Endpoint: GET /health
Reports overall system and dependency status without leaking credentials.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings
from app.retrieval.vector_store import vector_store
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health Diagnostics",
    description="Returns live status of backend services and dependencies without exposing credentials."
)
def health_endpoint(db: Session = Depends(get_db)):
    """
    Check overall health including MySQL and ChromaDB dependencies.
    """
    # 1. MySQL Check
    mysql_status = "connected"
    mysql_version = None
    try:
        mysql_version = db.execute(text("SELECT VERSION();")).scalar()
    except Exception as e:
        mysql_status = f"unhealthy: {type(e).__name__}"

    # 2. ChromaDB Check
    chroma_status = "available"
    collection_count = 0
    try:
        col = vector_store.get_collection()
        collection_count = col.count()
    except Exception as e:
        chroma_status = f"unavailable: {type(e).__name__}"

    overall_status = "healthy" if (mysql_status == "connected" and "available" in chroma_status) else "degraded"

    return HealthResponse(
        status=overall_status,
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        dependencies={
            "mysql": {
                "status": mysql_status,
                "database": settings.DB_NAME,
                "version": mysql_version,
                "host": f"{settings.DB_HOST}:{settings.DB_PORT}"
            },
            "chromadb": {
                "status": chroma_status,
                "collection": settings.CHROMA_COLLECTION_NAME,
                "total_vectors": collection_count
            },
            "langgraph": {
                "status": "ready"
            }
        }
    )
