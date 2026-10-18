from .health import router as health_router
from .chat import router as chat_router
from .ingest import router as ingest_router
from .escalations import router as escalations_router
from .reports import router as reports_router
from .clients import router as clients_router

__all__ = [
    "health_router",
    "chat_router",
    "ingest_router",
    "escalations_router",
    "reports_router",
    "clients_router"
]
