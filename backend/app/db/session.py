"""
Database Session and Engine Management
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.core.config import settings

# Database Engine
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base
Base = declarative_base()

# Restricted Read-Only Database Engine (SELECT-only account)
try:
    readonly_engine = create_engine(
        settings.READONLY_SQLALCHEMY_DATABASE_URI,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.DEBUG,
        connect_args={"connect_timeout": 5}
    )
    ReadOnlySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=readonly_engine)
except Exception:
    # Safe fallback if readonly user configuration is missing
    readonly_engine = engine
    ReadOnlySessionLocal = SessionLocal

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_readonly_db() -> Generator[Session, None, None]:
    """Dependency to yield a restricted read-only database session."""
    db = ReadOnlySessionLocal()
    try:
        yield db
    finally:
        db.close()
