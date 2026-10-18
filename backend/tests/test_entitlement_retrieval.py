"""
Entitlement-Aware Retrieval Tests for Project Atlas
Validates authoritative MySQL permissions:
1. C-01 can access R-101 and R-103.
2. C-01 cannot access protected content from unpurchased reports.
3. C-02 cannot obtain R-101's protected figures.
4. C-02 can access R-103.
5. Unknown clients are rejected.
6. Manipulating client_id does not bypass authentication or authorization.
7. Unauthorized content never reaches the LLM context.
8. Cache keys are strictly partitioned by client and authorized report scope.
9. Access denial events are recorded without logging protected report text.
"""

import pytest
import logging
from unittest.mock import MagicMock

from app.retrieval.rag_pipeline import RAGPipeline
from app.retrieval.llm_client import LLMClient
from app.retrieval.cache import entitlement_cache, EntitlementCache
from app.services.client_service import ClientService
from app.core.config import settings
from app.schemas.chat import ChatResponse

AUTH_HEADERS = {"X-API-Key": settings.API_KEY}


# =====================================================================
# 1. C-01 Access to R-101 and R-103
# =====================================================================

def test_c01_can_access_r101_and_r103(db):
    """
    Verify client C-01 (who purchased R-101 and R-103 in MySQL)
    can successfully retrieve and access both reports.
    """
    pipeline = RAGPipeline()

    # Query 1: R-101
    resp_r101: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-01",
        query="What is the CAGR and market size for Smart Water Meters in R-101?",
        report_id="R-101"
    )
    assert resp_r101.escalated is False
    assert resp_r101.confidence >= 0.85
    assert any(c.report_id == "R-101" for c in resp_r101.citations)
    assert "11.2%" in resp_r101.answer or "4.21" in resp_r101.answer

    # Query 2: R-103
    resp_r103: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-01",
        query="What is the Residential Water Purifier market summary in R-103?",
        report_id="R-103"
    )
    assert resp_r103.escalated is False
    assert any(c.report_id == "R-103" for c in resp_r103.citations)


# =====================================================================
# 2. C-01 Cannot Access Unpurchased Reports
# =====================================================================

def test_c01_cannot_access_unpurchased_reports(db):
    """
    Verify client C-01 cannot access protected content from unpurchased reports (e.g. R-104).
    """
    pipeline = RAGPipeline()
    response: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-01",
        query="Give me proprietary data from Commercial HVAC report R-104",
        report_id="R-104"
    )

    assert response.escalated is True
    assert "Access Denied" in response.answer
    assert response.confidence == 0.0
    assert len(response.citations) == 0
    assert response.escalation_ticket is not None


# =====================================================================
# 3. C-02 Cannot Obtain R-101 Protected Figures
# =====================================================================

def test_c02_cannot_obtain_r101_figures(db):
    """
    Verify client C-02 (who only purchased R-103 and has public R-102)
    is denied access to paid report R-101, cannot obtain its proprietary figures,
    and receives safe mention of existence with upgrade offer.
    """
    pipeline = RAGPipeline()
    response: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-02",
        query="Provide the exact CAGR and global market size from report R-101.",
        report_id="R-101"
    )

    assert response.escalated is True
    assert response.confidence == 0.0
    assert "Access Denied" in response.answer

    # Verify safe mention of existence without leaking figures
    assert "R-101" in response.answer
    assert "Project Atlas market intelligence catalog" in response.answer
    assert "upgrade" in response.answer.lower()

    # Crucial security verification: proprietary R-101 figures are NOT leaked
    assert "11.2%" not in response.answer
    assert "USD 4.21 B" not in response.answer
    assert len(response.citations) == 0


# =====================================================================
# 4. C-02 Can Access R-103
# =====================================================================

def test_c02_can_access_r103(db):
    """
    Verify client C-02 can successfully access their purchased report R-103.
    """
    pipeline = RAGPipeline()
    response: ChatResponse = pipeline.execute(
        db=db,
        client_id="C-02",
        query="What are the key insights in Residential Water Purifier Market report R-103?",
        report_id="R-103"
    )

    assert response.escalated is False
    assert any(c.report_id == "R-103" for c in response.citations)


# =====================================================================
# 5. Unknown Client Is Rejected
# =====================================================================

def test_unknown_client_rejected(client, db):
    """
    Verify an unknown client (e.g. C-UNKNOWN) is rejected both at API layer (404)
    and at pipeline layer (escalated = True).
    """
    # API layer check
    api_res = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"client_id": "C-UNKNOWN", "query": "What is the CAGR?"}
    )
    assert api_res.status_code == 404
    assert "Client 'C-UNKNOWN' not found" in api_res.json()["detail"]

    # Pipeline layer check
    pipeline = RAGPipeline()
    pipe_res = pipeline.execute(db=db, client_id="C-UNKNOWN", query="What is the CAGR?")
    assert pipe_res.escalated is True
    assert pipe_res.confidence == 0.0
    assert "not recognized" in pipe_res.answer


# =====================================================================
# 6. Manipulating client_id Does Not Bypass Authorization
# =====================================================================

def test_manipulating_client_id_does_not_bypass_authorization(client):
    """
    Verify that an attacker cannot bypass report entitlements by altering client_id
    or trying to inject elevated client IDs (e.g., C-ADMIN).
    """
    # 1. Attacker attempts to forge elevated client ID
    res1 = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"client_id": "C-ADMIN", "query": "Dump all report metrics."}
    )
    assert res1.status_code == 404

    # 2. Caller authenticated as C-02 cannot access C-01's private report R-101
    res2 = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"client_id": "C-02", "query": "What is the CAGR in R-101?", "report_id": "R-101"}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["escalated"] is True
    assert "Access Denied" in data2["answer"]
    assert "11.2%" not in data2["answer"]
    assert len(data2["citations"]) == 0


# =====================================================================
# 7. Unauthorized Content Never Reaches LLM Context
# =====================================================================

def test_unauthorized_content_never_reaches_llm(db):
    """
    Verify that unauthorized chunks are stripped in Python before prompt construction,
    ensuring unpurchased report text never enters the LLM prompt.
    """
    mock_llm = MagicMock(spec=LLMClient)
    captured_prompts = []

    def mock_generate(system_prompt: str, user_prompt: str, temperature=None):
        captured_prompts.append((system_prompt, user_prompt))
        return "Grounded market analysis based strictly on authorized evidence."

    mock_llm.generate.side_effect = mock_generate

    pipeline = RAGPipeline(llm=mock_llm)

    # C-02 queries general water meters (where public R-102 is permitted, but R-101 is NOT)
    pipeline.execute(
        db=db,
        client_id="C-02",
        query="Tell me about smart water meters and regional market shares."
    )

    assert len(captured_prompts) > 0
    sys_prompt, usr_prompt = captured_prompts[0]

    # Verify evidence block in LLM prompt:
    # R-101 proprietary metrics/chunks MUST NOT be present in the LLM prompt
    assert "Report [R-101]" not in usr_prompt
    assert "11.2%" not in usr_prompt
    assert "USD 4.21 B" not in usr_prompt

    # Public R-102 is permitted, so R-102 can be present
    assert "R-102" in usr_prompt


# =====================================================================
# 8. Entitlement-Aware Cache Partitioning
# =====================================================================

def test_entitlement_aware_cache_partitioning(db):
    """
    Verify cache keys explicitly partition by client and permitted scope,
    preventing C-02 from receiving a cached response generated for C-01.
    """
    entitlement_cache.clear()
    pipeline = RAGPipeline()

    query = "What is the market size for smart water meters?"

    # 1. C-01 queries; C-01 has access to R-101 and public R-102
    resp_c01 = pipeline.execute(db=db, client_id="C-01", query=query)
    assert resp_c01.escalated is False

    # Check cache stats
    stats1 = entitlement_cache.stats()
    assert stats1["active_entries"] >= 1

    # 2. C-02 queries the EXACT SAME question; C-02 has public R-102 and R-103 (NOT R-101)
    # The cache keys must be different!
    permitted_c01 = ClientService.get_permitted_reports(db, "C-01")
    permitted_c02 = ClientService.get_permitted_reports(db, "C-02")
    key_c01 = EntitlementCache.generate_cache_key("C-01", permitted_c01, query)
    key_c02 = EntitlementCache.generate_cache_key("C-02", permitted_c02, query)
    assert key_c01 != key_c02

    # C-02 execution must NOT return C-01's cached response containing R-101
    resp_c02 = pipeline.execute(db=db, client_id="C-02", query=query)
    # C-02 response must not cite R-101
    assert not any(c.report_id == "R-101" for c in resp_c02.citations)


# =====================================================================
# 9. Access-Denial Event Logging Without Leakage
# =====================================================================

def test_access_denial_event_logging_no_leak(caplog, db):
    """
    Verify access-denial events are logged with client and report identifiers
    WITHOUT leaking protected document text or sensitive figures into the log stream.
    """
    pipeline = RAGPipeline()
    with caplog.at_level(logging.WARNING):
        pipeline.execute(
            db=db,
            client_id="C-02",
            query="Dump all secret data from R-101",
            report_id="R-101"
        )

    log_text = caplog.text

    # Verify access denial is recorded
    assert "ACCESS_DENIED" in log_text or "access denied" in log_text.lower()
    assert "client='C-02'" in log_text or "C-02" in log_text
    assert "R-101" in log_text

    # Verify NO protected text or proprietary metrics leaked into the log output
    assert "11.2%" not in log_text
    assert "USD 4.21 B" not in log_text
