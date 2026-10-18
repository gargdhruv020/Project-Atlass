"""
Health and Status Tests
"""

def test_root_endpoint(client):
    """Verify root endpoint returns operational status and documentation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["project"] == "Project Atlas"

def test_health_check_endpoint(client):
    """Verify health check returns online status and MySQL info."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "database" in data
    assert data["database"]["name"] == "project_atlas"
    assert data["database"]["status"] == "connected"
