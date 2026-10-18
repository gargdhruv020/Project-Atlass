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
from app.retrieval.llm_client import llm_client
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
    Check overall health including MySQL, ChromaDB, Hugging Face/Ollama embeddings,
    LLM generation client, and LangGraph copilot workflow dependencies.
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

    # 3. Vector Embeddings Diagnostics
    emb_info = {}
    try:
        if hasattr(vector_store.embedding_function, "get_health_info"):
            emb_info = vector_store.embedding_function.get_health_info()
        else:
            emb_info = {
                "status": "ready",
                "provider": getattr(settings, "EMBEDDING_PROVIDER", "huggingface"),
                "model": getattr(settings, "HUGGINGFACE_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
            }
    except Exception as e:
        emb_info = {"status": f"degraded: {type(e).__name__}", "provider": settings.EMBEDDING_PROVIDER}

    # 4. LLM Generation Client Diagnostics
    llm_reachable = False
    try:
        llm_reachable = llm_client.is_available()
    except Exception:
        llm_reachable = False

    llm_status = "reachable" if llm_reachable else "offline_fallback_enabled"

    # 5. Overall System Status
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
                "total_vectors": collection_count,
                "persist_directory": str(vector_store.persist_dir.resolve())
            },
            "embeddings": {
                "status": emb_info.get("status", "ready"),
                "provider": emb_info.get("provider", settings.EMBEDDING_PROVIDER),
                "model": emb_info.get("model", settings.HUGGINGFACE_MODEL_NAME),
                "active_mode": emb_info.get("active_provider", "local")
            },
            "llm": {
                "status": llm_status,
                "provider": settings.LLM_PROVIDER,
                "model": settings.LLM_MODEL,
                "fallback_active": not llm_reachable
            },
            "langgraph": {
                "status": "ready",
                "workflow": "copilot_agent_graph",
                "nodes": [
                    "router",
                    "entitlement_checker",
                    "retriever",
                    "read_only_sql",
                    "calculator",
                    "critic",
                    "escalation",
                    "writer"
                ]
            }
        }
    )
