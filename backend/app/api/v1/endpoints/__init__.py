from .health import router as health_router
from .reports import router as reports_router
from .clients import router as clients_router
from .query import router as query_router

__all__ = ["health_router", "reports_router", "clients_router", "query_router"]
