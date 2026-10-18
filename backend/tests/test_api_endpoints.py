"""
API Endpoint Integration Tests
Validates authentication, input validation, client authorization,
and expected structured responses for /chat, /ingest, /escalations, /health.
"""

import pytest
from app.core.config import settings

AUTH_HEADERS = {"X-API-Key": settings.API_KEY}
BEARER_HEADERS = {"Authorization": f"Bearer {settings.API_KEY}"}

# =====================================================================
# 1. POST /chat Tests
# =====================================================================

def test_chat_authentication_missing(client):
    """Verify /chat rejects unauthenticated requests with 401."""
    response = client.post("/chat", json={"client_id": "C-01", "query": "What is the CAGR?"})
    assert response.status_code == 401
    assert "Invalid or missing API key" in response.json()["detail"]

def test_chat_authentication_invalid(client):
    """Verify /chat rejects requests with an invalid API key."""
    response = client.post(
        "/chat",
        headers={"X-API-Key": "invalid-wrong-key"},
        json={"client_id": "C-01", "query": "What is the CAGR?"}
    )
    assert response.status_code == 401

def test_chat_validation_missing_client_id(client):
    """Verify /chat validates presence of client_id with 422."""
    response = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"query": "What is the market size?"}
    )
    assert response.status_code == 422
    assert "detail" in response.json()

def test_chat_validation_empty_query(client):
    """Verify /chat validates query minimum length with 422."""
    response = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"client_id": "C-01", "query": ""}
    )
    assert response.status_code == 422

def test_chat_validation_oversized_query(client):
    """Verify /chat rejects query exceeding 4000 characters with 422."""
    long_query = "A" * 4001
    response = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"client_id": "C-01", "query": long_query}
    )
    assert response.status_code == 422

def test_chat_client_not_found(client):
    """Verify /chat returns 404 when client_id is not in database."""
    response = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"client_id": "C-NONEXISTENT", "query": "What is the CAGR?"}
    )
    assert response.status_code == 404
    assert "Client 'C-NONEXISTENT' not found" in response.json()["detail"]

def test_chat_success_authorized_client(client):
    """
    Verify /chat returns 200 with all 6 required fields:
    answer, citations, confidence, conflicts, derived_values, escalated.
    """
    response = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={
            "client_id": "C-01",
            "query": "What is the CAGR for Smart Water Meters in R-101?",
            "report_id": "R-101"
        }
    )
    assert response.status_code == 200
    data = response.json()

    # Verify all 6 mandatory top-level response fields
    assert "answer" in data
    assert "citations" in data
    assert "confidence" in data
    assert "conflicts" in data
    assert "derived_values" in data
    assert "escalated" in data

    # Verify field types and values
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) > 0
    assert isinstance(data["confidence"], float)
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["confidence"] >= 0.8  # high confidence for exact match
    assert isinstance(data["conflicts"], list)
    assert isinstance(data["derived_values"], dict)
    assert data["escalated"] is False
    assert data["client_id"] == "C-01"

    # Verify citation contents
    citation = data["citations"][0]
    assert citation["report_id"] == "R-101"
    assert citation["metric"] == "CAGR"
    assert citation["value"] == "11.2%"
    assert citation["source_type"] == "relational_sql"

def test_chat_unauthorized_report_access_escalates(client):
    """
    Verify client C-02 querying paid report R-101 is denied and escalated.
    """
    response = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={
            "client_id": "C-02",
            "query": "What is the market size in R-101?",
            "report_id": "R-101"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "Access Denied" in data["answer"]
    assert data["escalated"] is True
    assert data["confidence"] == 0.0
    assert data["escalation_ticket"] is not None

def test_chat_explicit_escalation_request(client):
    """Verify that asking to talk to an analyst sets escalated=True."""
    response = client.post(
        "/chat",
        headers=BEARER_HEADERS,
        json={
            "client_id": "C-01",
            "query": "Please escalate this request to a human analyst for detailed forecasting."
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["escalated"] is True
    assert data["escalation_ticket"] is not None

# =====================================================================
# 2. POST /ingest Tests
# =====================================================================

def test_ingest_authentication_missing(client):
    """Verify /ingest rejects unauthenticated requests with 401."""
    response = client.post("/ingest", json={"report_id": "R-105", "content": "Sample text"})
    assert response.status_code == 401

def test_ingest_validation_missing_content(client):
    """Verify /ingest rejects request lacking both content and file_path with 400."""
    response = client.post(
        "/ingest",
        headers=AUTH_HEADERS,
        json={"report_id": "R-105"}
    )
    assert response.status_code == 400

def test_ingest_success(client):
    """Verify /ingest successfully chunks and persists content into ChromaDB."""
    sample_text = (
        "The smart water meter market is undergoing rapid digital transformation. "
        "Advanced metering infrastructure enables real-time leak detection, "
        "reducing non-revenue water losses significantly across municipal water grids."
    )
    response = client.post(
        "/ingest",
        headers=AUTH_HEADERS,
        json={
            "report_id": "R-105",
            "title": "Smart Meter Digital Transformation 2026",
            "content": sample_text,
            "metadata": {"sector": "Utilities", "version": "1.0"}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["report_id"] == "R-105"
    assert data["chunks_ingested"] >= 1
    assert "market_reports" in data["collection"]

# =====================================================================
# 3. GET /escalations Tests
# =====================================================================

def test_escalations_authentication_missing(client):
    """Verify /escalations rejects unauthenticated requests with 401."""
    response = client.get("/escalations")
    assert response.status_code == 401

def test_escalations_success(client):
    """Verify /escalations retrieves ticket list for authenticated caller."""
    response = client.get("/escalations", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)

def test_escalations_client_filter_and_validation(client):
    """Verify /escalations validates client_id and filters results."""
    # Invalid client
    err_res = client.get("/escalations?client_id=C-INVALID", headers=AUTH_HEADERS)
    assert err_res.status_code == 404

    # Valid client
    ok_res = client.get("/escalations?client_id=C-02", headers=AUTH_HEADERS)
    assert ok_res.status_code == 200
    data = ok_res.json()
    for item in data["items"]:
        assert item["client_id"] == "C-02"
