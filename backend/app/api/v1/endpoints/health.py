"""
Health and Diagnostic Endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Check overall service health, including MySQL database connectivity.
    """
    db_status = "connected"
    mysql_version = None
    try:
        mysql_version = db.execute(text("SELECT VERSION();")).scalar()
    except Exception as e:
        db_status = f"unhealthy: {e}"

    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": {
            "name": settings.DB_NAME,
            "status": db_status,
            "version": mysql_version,
            "host": f"{settings.DB_HOST}:{settings.DB_PORT}"
        },
        "vector_store": {
            "type": "ChromaDB (Local)",
            "persist_directory": settings.CHROMA_PERSIST_DIRECTORY
        }
    }
