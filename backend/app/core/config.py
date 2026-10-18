"""
Application Configuration
Loads settings from environment variables and .env file.
"""

import os
from pathlib import Path
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
    CHROMA_COLLECTION_NAME: str = "market_reports"

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
