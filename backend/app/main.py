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

from app.core.config import settings
from app.db.session import engine
from app.api.v1.router import api_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.ingest import router as ingest_router
from app.api.v1.endpoints.escalations import router as escalations_router
from app.api.v1.endpoints.health import router as health_router
from app.observability.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    
    # Verify MySQL connectivity
    try:
        with engine.connect() as conn:
            db_name = conn.execute(text("SELECT DATABASE();")).scalar()
            version = conn.execute(text("SELECT VERSION();")).scalar()
            logger.info(f"MySQL Connected: database='{db_name}', version='{version}'")
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
