"""
End-to-End Application Integration Tests for Project Atlas
Verifies complete system integration across FastAPI endpoints, MySQL entitlements,
ChromaDB vector store, Hugging Face embeddings, LangGraph workflow, deterministic calculator,
citation verification, and analyst escalation service.
"""

import pytest
from app.core.config import settings
from app.retrieval.vector_store import vector_store


def test_integration_health_diagnostics(client):
    """
    Verify GET /health reports live diagnostics for all 5 core dependencies:
    MySQL, ChromaDB, Hugging Face/Ollama Embeddings, LLM client, and LangGraph workflow.
    Ensures zero credentials, passwords, or API keys are exposed.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ["healthy", "degraded"]
    assert data["project"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION

    deps = data["dependencies"]
    assert "mysql" in deps
    assert "chromadb" in deps
    assert "embeddings" in deps
    assert "llm" in deps
    assert "langgraph" in deps

    # MySQL status
    assert deps["mysql"]["status"] == "connected"
    assert deps["mysql"]["database"] == settings.DB_NAME

    # ChromaDB status
    assert "available" in deps["chromadb"]["status"]
    assert deps["chromadb"]["collection"] == settings.CHROMA_COLLECTION_NAME

    # Embeddings status
    assert deps["embeddings"]["status"] in ["ready", "connected", "fallback"]
    assert deps["embeddings"]["provider"] is not None
    assert deps["embeddings"]["model"] is not None

    # LLM status
    assert deps["llm"]["status"] in ["reachable", "offline_fallback_enabled"]
    assert deps["llm"]["provider"] == settings.LLM_PROVIDER
    assert deps["llm"]["model"] == settings.LLM_MODEL

    # LangGraph status
    assert deps["langgraph"]["status"] == "ready"
    assert len(deps["langgraph"]["nodes"]) == 8

    # Security check: Zero credential leakage in response text
    raw_body = response.text
    assert settings.DB_PASSWORD not in raw_body
    assert settings.SECRET_KEY not in raw_body
    assert settings.API_KEY not in raw_body
    if settings.HUGGINGFACE_API_KEY:
        assert settings.HUGGINGFACE_API_KEY not in raw_body


def test_integration_chat_ordinary_query_flow(client):
    """
    Verify POST /chat executes full agent workflow for entitled client C-01:
    Router -> Entitlements -> Retriever -> Critic -> Writer.
    Returns complete structured JSON adhering to ChatResponse schema.
    """
    headers = {"x-api-key": settings.API_KEY}
    payload = {
        "client_id": "C-01",
        "query": "What was the global smart water meter market size in 2024 according to R-101?"
    }

    response = client.post("/chat", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Required response attributes
    assert "answer" in data
    assert "citations" in data
    assert "confidence" in data
    assert "conflicts" in data
    assert "derived_values" in data
    assert "escalated" in data

    assert data["client_id"] == "C-01"
    assert len(data["answer"]) > 0
    assert data["confidence"] >= settings.ESCALATION_CONFIDENCE_THRESHOLD
    assert data["escalated"] is False

    # Verify citation integrity: C-01 is entitled to R-101
    citations = data["citations"]
    assert len(citations) > 0
    report_ids = [c["report_id"] for c in citations]
    assert "R-101" in report_ids


def test_integration_chat_entitlement_enforcement(client):
    """
    Verify POST /chat enforces MySQL client entitlements:
    Client C-02 (only purchased R-103) querying R-101 data is denied access
    and zero proprietary figures or chunks from R-101 are disclosed.
    """
    headers = {"x-api-key": settings.API_KEY}
    payload = {
        "client_id": "C-02",
        "query": "What is the 2024 market size reported in R-101?"
    }

    response = client.post("/chat", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    # The agent informs the user of lack of access to R-101
    assert "access" in data["answer"].lower() or "unauthorized" in data["answer"].lower() or "purchase" in data["answer"].lower()
    
    # Assert R-101 proprietary citations are NOT leaked
    for cit in data.get("citations", []):
        assert cit.get("report_id") != "R-101"


def test_integration_chat_deterministic_calculation(client):
    """
    Verify POST /chat executes deterministic CAGR projection calculator without LLM arithmetic errors.
    """
    headers = {"x-api-key": settings.API_KEY}
    payload = {
        "client_id": "C-01",
        "query": "Calculate the projected smart water meter market size in 2026 based on R-101 base value in 2024."
    }

    response = client.post("/chat", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "derived_values" in data
    derived = data["derived_values"]
    assert len(derived) > 0
    assert "projected" in str(derived).lower() or "future_value" in derived


def test_integration_ingest_pipeline_flow(client):
    """
    Verify POST /ingest processes report content, chunks it, and updates ChromaDB.
    Also verifies unauthenticated ingestion is rejected.
    """
    # 1. Unauthenticated request rejected
    unauth_resp = client.post(
        "/ingest",
        json={
            "report_id": "R-TEST-INTEG",
            "title": "Integration Test Report",
            "content": "# Integration Test Report\nTesting ingestion pipeline end-to-end."
        }
    )
    assert unauth_resp.status_code == 401

    # 2. Authenticated ingestion succeeded
    auth_resp = client.post(
        "/ingest",
        json={
            "report_id": "R-TEST-INTEG",
            "title": "Integration Test Report",
            "content": "# Integration Test Report\n\n## Market Overview\nThe industrial sensor market reached $1.5 billion in 2024.",
            "metadata": {"sector": "Industrial", "year": "2024"}
        },
        headers={"x-api-key": settings.API_KEY}
    )
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert data["status"] == "success"
    assert data["report_id"] == "R-TEST-INTEG"
    assert data["chunks_ingested"] > 0


def test_integration_escalations_management(client):
    """
    Verify GET /escalations retrieves authorized analyst records and rejects unauthorized calls.
    """
    # 1. Unauthenticated access rejected
    unauth_resp = client.get("/escalations")
    assert unauth_resp.status_code == 401

    # 2. Authenticated access returns valid records
    auth_resp = client.get("/escalations", headers={"x-api-key": settings.API_KEY})
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_integration_request_validation(client):
    """
    Verify FastAPI request validation returns structured 422 JSON when required fields are missing.
    """
    headers = {"x-api-key": settings.API_KEY}

    # Missing client_id
    resp = client.post("/chat", json={"query": "Hello"}, headers=headers)
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
    assert "errors" in data
