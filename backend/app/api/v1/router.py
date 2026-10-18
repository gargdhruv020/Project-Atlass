"""
API v1 Router Aggregator
Combines chat, ingest, escalations, health, reports, and clients into api_router.
"""

from fastapi import APIRouter
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.ingest import router as ingest_router
from app.api.v1.endpoints.escalations import router as escalations_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.clients import router as clients_router
from app.api.v1.endpoints.conversations import router as conversations_router

api_router = APIRouter()
api_router.include_router(chat_router)
api_router.include_router(ingest_router)
api_router.include_router(escalations_router)
api_router.include_router(health_router)
api_router.include_router(reports_router)
api_router.include_router(clients_router)
api_router.include_router(conversations_router)
