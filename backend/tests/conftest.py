"""
Pytest Fixtures for Project Atlas Backend Tests
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.db.session import get_db, SessionLocal

@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="function")
def db():
    """Database session fixture with clean per-test transaction scope."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
