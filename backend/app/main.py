"""
Project Atlas - FastAPI Application
AI-Powered Market Research Report Copilot Backend.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.db.session import engine
from app.api.v1.router import api_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.ingest import router as ingest_router
from app.api.v1.endpoints.escalations import router as escalations_router
from app.api.v1.endpoints.health import router as health_router
from app.observability.logger import logger

class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Enforces request processing timeout across all API endpoints."""
    async def dispatch(self, request: Request, call_next):
        timeout = float(getattr(settings, "REQUEST_TIMEOUT_SECONDS", 30))
        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Request timeout after {timeout}s: {request.method} {request.url.path}")
            return JSONResponse(
                status_code=504,
                content={"detail": f"Request processing timed out after {timeout} seconds"}
            )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    
    # Verify MySQL connectivity and ensure escalation_tickets exists
    try:
        from app.models.escalation import EscalationTicket
        EscalationTicket.__table__.create(bind=engine, checkfirst=True)
        with engine.connect() as conn:
            db_name = conn.execute(text("SELECT DATABASE();")).scalar()
            version = conn.execute(text("SELECT VERSION();")).scalar()
            logger.info(f"MySQL Connected: database='{db_name}', version='{version}' (escalation_tickets verified)")
    except Exception as e:
        logger.error(f"MySQL connection warning: {e}")

    yield

    logger.info(f"Shutting down {settings.PROJECT_NAME}...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered Market Research Report Copilot API integrating LangGraph, MySQL, and ChromaDB.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Request Timeout Middleware
app.add_middleware(RequestTimeoutMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Validation Error Handler for consistent structured JSON
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field,
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error")
        })
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "errors": errors
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None)
        )
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred while processing request."}
    )

# Mount primary endpoints at root level (/chat, /ingest, /escalations, /health)
app.include_router(chat_router)
app.include_router(ingest_router)
app.include_router(escalations_router)
app.include_router(health_router)

# Mount versioned API routes (/api/v1/...)
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
def root():
    """Root status and documentation endpoints."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "chat": "POST /chat",
            "ingest": "POST /ingest",
            "escalations": "GET /escalations",
            "health": "GET /health"
        },
        "api_v1": settings.API_V1_STR,
        "status": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
