"""
API v1 Router Aggregator
Combines health, reports, clients, and copilot endpoints into a single v1 router.
"""

from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.clients import router as clients_router
from app.api.v1.endpoints.query import router as query_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(reports_router)
api_router.include_router(clients_router)
api_router.include_router(query_router)
