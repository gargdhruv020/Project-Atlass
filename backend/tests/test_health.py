"""
Health and Status Tests
Verifies /health endpoint diagnostic reporting without secret exposure.
"""

from app.core.config import settings

def test_root_endpoint(client):
    """Verify root endpoint returns operational status and documentation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["project"] == "Project Atlas"
    assert "endpoints" in data

def test_health_check_endpoint_root(client):
    """Verify GET /health returns dependencies and zero leaked credentials."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["project"] == "Project Atlas"
    assert "dependencies" in data
    
    # MySQL dependency check
    assert "mysql" in data["dependencies"]
    assert data["dependencies"]["mysql"]["status"] == "connected"
    assert data["dependencies"]["mysql"]["database"] == "project_atlas"
    
    # ChromaDB dependency check
    assert "chromadb" in data["dependencies"]
    assert "available" in data["dependencies"]["chromadb"]["status"]

    # Security check: verify no database password or secret keys are exposed
    raw_text = response.text
    assert settings.DB_PASSWORD not in raw_text
    assert settings.API_KEY not in raw_text

def test_health_check_endpoint_v1(client):
    """Verify GET /api/v1/health also functions identically."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
