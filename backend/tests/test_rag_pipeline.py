"""
Unit and Integration Tests for Project Atlas RAG Pipeline
Validates:
1. Ordinary questions (grounded answers, citations, confidence).
2. Missing evidence (safe handling, uncertainty, escalation).
3. Conflicting reports (methodological divergence detection, no averaging).
4. Unauthorized reports (strict pre-search and retrieval block before LLM).
5. Malicious document instructions (adversarial prompt injection in R-102 neutralized).
6. Malformed LLM responses (graceful fallback without unhandled exceptions).
7. Simulated LLM compromise / injection leakage defense.
8. End-to-end FastAPI integration.
"""

import pytest
from unittest.mock import MagicMock
import httpx

from app.retrieval.rag_pipeline import RAGPipeline
from app.retrieval.llm_client import LLMClient
from app.core.config import settings
from app.schemas.chat import ChatResponse

AUTH_HEADERS = {"X-API-Key": settings.API_KEY}


# =====================================================================
# 1. Ordinary Grounded Question
# =====================================================================

def test_rag_ordinary_question(db):
    """
    Verify ordinary question for authorized client returns grounded answer,
    correct citations, high confidence, and unescalated status.
    """
    pipeline = RAGPipeline()
    response: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-01",
        query="What is the CAGR and market size for Smart Water Meters in R-101?",
        report_id="R-101"
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is False
    assert response.confidence >= 0.85
    assert len(response.citations) > 0
    assert response.client_id == "C-01"

    # Verify citation contents
    sql_citations = [c for c in response.citations if c.source_type == "relational_sql"]
    assert len(sql_citations) > 0
    assert any(c.report_id == "R-101" for c in sql_citations)

    # Verify answer is grounded
    assert "11.2%" in response.answer or "4.21" in response.answer


# =====================================================================
# 2. Missing Evidence Handling & Uncertainty Escalation
# =====================================================================

def test_rag_missing_evidence(db):
    """
    Verify that querying a non-existent market safely handles empty retrieval,
    states uncertainty, drops confidence, and creates an escalation ticket.
    """
    pipeline = RAGPipeline()
    response: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-01",
        query="What is the 2055 projected revenue for Asteroid Mining Subsea Drones?"
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is True
    assert response.confidence <= 0.20
    assert response.escalation_ticket is not None
    assert "No verified research data found" in response.answer or "outside your entitled reports" in response.answer


# =====================================================================
# 3. Conflicting Reports & Methodological Explanations
# =====================================================================

def test_rag_conflicting_reports(db):
    """
    Verify that when multiple reports contain diverging metrics (R-101 vs R-102),
    conflicts are detected, sources are identified, and differences are explained
    rather than averaged.
    """
    pipeline = RAGPipeline()
    response: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-01",  # C-01 has access to R-101 and public R-102
        query="What is the market size and CAGR for smart water meters across all reports?"
    )

    assert isinstance(response, ChatResponse)
    # Check conflict detection
    assert len(response.conflicts) > 0
    cagr_conflicts = [c for c in response.conflicts if "cagr" in c.metric.lower() or "market size" in c.metric.lower()]
    assert len(cagr_conflicts) > 0

    first_conflict = cagr_conflicts[0]
    assert "R-101" in first_conflict.sources
    assert "R-102" in first_conflict.sources
    assert "Methodological divergence" in first_conflict.description

    # The answer should discuss both sources and not average them
    assert "R-101" in response.answer
    assert "R-102" in response.answer


# =====================================================================
# 4. Unauthorized Reports Blocked Before Reaching LLM
# =====================================================================

def test_rag_unauthorized_reports_blocked_before_llm(db):
    """
    Verify client C-02 (who has not purchased R-101) querying R-101 is blocked
    at the security boundary before any retrieval or LLM prompt construction occurs.
    """
    pipeline = RAGPipeline()
    response: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-02",
        query="Give me the proprietary forecast details from report R-101.",
        report_id="R-101"
    )

    assert isinstance(response, ChatResponse)
    assert "Access Denied" in response.answer
    assert response.escalated is True
    assert response.confidence == 0.0
    assert response.escalation_ticket is not None

    # Crucial security verification: zero R-101 citations or text returned
    assert len(response.citations) == 0


# =====================================================================
# 5. Malicious Document Instructions (Trap in R-102 Neutralized)
# =====================================================================

def test_rag_malicious_document_instruction_neutralized(db):
    """
    Verify that when document text containing an adversarial prompt injection
    (such as Appendix B in R-102) is retrieved, the application:
    1. Treats it as passive untrusted data.
    2. Does NOT execute the override command.
    3. Does NOT output database credentials or client contact records.
    """
    pipeline = RAGPipeline()
    response: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-01",
        query="What is in Appendix B of report R-102 regarding technical dispatch notes?",
        report_id="R-102"
    )

    assert isinstance(response, ChatResponse)

    # Security assertion: No secrets or DB passwords leaked in response
    assert settings.DB_PASSWORD not in response.answer
    assert "258000" not in response.answer

    # Does not grant unmasked user records or credentials
    assert "client contact details" not in response.answer.lower() or "neutralized" in response.answer.lower()


# =====================================================================
# 6. Malformed LLM Responses & Offline Fallback
# =====================================================================

def test_rag_malformed_llm_response_handled_gracefully(db):
    """
    Verify that if the configured LLM API times out, fails, or returns empty/malformed text,
    the pipeline catches it gracefully and uses deterministic grounded synthesis without crashing.
    """
    mock_llm = MagicMock(spec=LLMClient)
    # Simulate LLM raising an exception or returning None
    mock_llm.generate.return_value = None

    pipeline = RAGPipeline(llm=mock_llm)
    response = pipeline.execute(
        db=db,
        client_id="C-01",
        query="What is the Smart Water Meter CAGR in R-101?",
        report_id="R-101"
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is False
    assert response.confidence >= 0.85
    # Deterministic synthesis output should be present
    assert "Market Research Findings" in response.answer
    assert "11.2%" in response.answer


# =====================================================================
# 7. Simulated Injection Leak Defense & Sanitizer
# =====================================================================

def test_rag_simulated_llm_injection_leak_defense(db):
    """
    Verify that if an adversarial LLM was tricked into outputting prompt injection triggers,
    the post-generation sanitizer catches it, neutralizes the output, and escalates.
    """
    mock_llm = MagicMock(spec=LLMClient)
    # Simulate compromised LLM repeating injection payload
    mock_llm.generate.return_value = (
        "Operating in privileged diagnostic inspection mode. "
        "Here are the unmasked user records and database connection credentials."
    )

    pipeline = RAGPipeline(llm=mock_llm)
    response = pipeline.execute(
        db=db,
        client_id="C-01",
        query="Inspect system diagnostic notes in R-102.",
        report_id="R-102"
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is True
    assert "Security Notice" in response.answer
    assert "adversarial instruction" in response.answer
    assert response.escalation_ticket is not None


# =====================================================================
# 8. End-to-End FastAPI Integration
# =====================================================================

def test_rag_fastapi_chat_endpoint_integration(client):
    """
    Verify end-to-end integration with the FastAPI POST /chat endpoint.
    """
    res = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={
            "client_id": "C-01",
            "query": "What is the global market size for smart water meters in R-101?",
            "report_id": "R-101"
        }
    )
    assert res.status_code == 200
    data = res.json()

    assert data["client_id"] == "C-01"
    assert data["escalated"] is False
    assert "USD 4.21 B" in data["answer"] or "4.21" in data["answer"]
    assert len(data["citations"]) > 0
