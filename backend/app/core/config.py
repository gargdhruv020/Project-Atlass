"""
Application Configuration
Loads settings from environment variables and .env file.
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Base Directory: root of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Project Info
    PROJECT_NAME: str = "Project Atlas"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = Field(default=False, alias="DEBUG")
    
    # Server
    HOST: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    PORT: int = Field(default=8000, alias="BACKEND_PORT")
    REQUEST_TIMEOUT_SECONDS: int = 30
    MAX_REQUEST_SIZE_BYTES: int = 10_000_000

    # MySQL Database Settings
    DB_HOST: str = Field(default="127.0.0.1", alias="DB_HOST")
    DB_PORT: int = Field(default=3306, alias="DB_PORT")
    DB_USER: str = Field(default="root", alias="DB_USER")
    DB_PASSWORD: str = Field(default="258000", alias="DB_PASSWORD")
    DB_NAME: str = Field(default="project_atlas", alias="DB_NAME")

    # ChromaDB Settings
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default=str(BASE_DIR / "chroma_data"),
        alias="CHROMA_PERSIST_DIRECTORY"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="market_reports",
        alias="CHROMA_COLLECTION_NAME"
    )

    # Embedding Settings (Local Ollama)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL"
    )
    OLLAMA_MODEL: str = Field(
        default="nomic-embed-text",
        alias="OLLAMA_MODEL"
    )

    # LLM Settings
    LLM_PROVIDER: str = Field(
        default="ollama",
        alias="LLM_PROVIDER"
    )
    LLM_MODEL: str = Field(
        default="llama3.2",
        alias="LLM_MODEL"
    )
    LLM_API_BASE: str = Field(
        default="http://localhost:11434",
        alias="LLM_API_BASE"
    )
    LLM_API_KEY: Optional[str] = Field(
        default=None,
        alias="LLM_API_KEY"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.0,
        alias="LLM_TEMPERATURE"
    )

    # RAG Retrieval Settings
    RAG_SIMILARITY_THRESHOLD: float = Field(
        default=0.60,
        alias="RAG_SIMILARITY_THRESHOLD"
    )
    RAG_TOP_K: int = Field(
        default=4,
        alias="RAG_TOP_K"
    )

    # Escalation Settings
    ESCALATION_CONFIDENCE_THRESHOLD: float = Field(
        default=0.70,
        alias="ESCALATION_CONFIDENCE_THRESHOLD",
        description="Confidence threshold below which inquiries are escalated to human analysts"
    )

    # Documents & Ingestion
    DOCUMENTS_DIR: str = Field(
        default=str(BASE_DIR / "documents"),
        alias="DOCUMENTS_DIR"
    )

    # Security & API
    API_KEY: str = Field(default="atlas-dev-key-2026", alias="API_KEY")
    SECRET_KEY: str = Field(default="atlas-insecure-secret-key-change-in-production", alias="SECRET_KEY")
    CORS_ORIGINS: list[str] = ["*"]

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construct MySQL SQLAlchemy URI with encoded credentials."""
        import urllib.parse
        encoded_user = urllib.parse.quote_plus(self.DB_USER)
        encoded_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{encoded_user}:{encoded_password}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

settings = Settings()
