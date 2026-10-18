"""
Unit and Integration Tests for Analyst Escalation Workflow
Tests:
1. Low-confidence answer escalation (< ESCALATION_CONFIDENCE_THRESHOLD)
2. Missing evidence escalation
3. Conflicting sources requiring judgment
4. Unresolved calculation assumptions (forecast window extrapolation)
5. Database error handling without ticket ID fabrication
6. Duplicate escalation submission suppression
7. Successful persistence of tickets in MySQL (escalation_tickets)
8. Authorized access to GET /escalations with filtering
9. Rejection of unauthorized requests to GET /escalations
10. Normal queries do not escalate unnecessarily
11. Preservation of existing database records
"""

import pytest
from unittest.mock import patch
from sqlalchemy import text
from app.core.config import settings
from app.services.escalation_service import EscalationService
from app.models.escalation import EscalationTicket
from app.agents.workflow import run_copilot_workflow
from app.schemas.chat import ChatResponse

AUTH_HEADERS = {"X-API-Key": settings.API_KEY}


# =====================================================================
# 1. Escalation Trigger: Low Confidence Answers
# =====================================================================

def test_escalation_triggers_on_low_confidence(db):
    """
    Verify that when confidence drops below ESCALATION_CONFIDENCE_THRESHOLD,
    the workflow escalates, sets escalated=True, generates an escalation ticket,
    and returns a structured explanation.
    """
    from app.agents.nodes import critic_node, route_after_critic

    # 1. State unit test: dropped ungrounded citation sets confidence=0.55 < 0.70
    state = {
        "query": "Verify smart water meter metrics",
        "client_id": "C-01",
        "permitted_reports": ["R-101"],
        "retrieved_metrics": [{"report_id": "R-101", "metric": "Market size", "value": "USD 4.21 B"}],
        "retrieved_chunks": [],
        "citations": [
            {"report_id": "R-101", "metric": "Market size", "value": "USD 4.21 B", "page": 99}  # Fabricated page
        ]
    }
    critic_res = critic_node(state)
    assert critic_res["confidence_score"] < settings.ESCALATION_CONFIDENCE_THRESHOLD
    assert critic_res["escalated"] is True
    assert route_after_critic(critic_res) == "escalation"

    # 2. Configurable threshold test: setting threshold to 0.98 forces factual query (0.90) to escalate
    with patch.object(settings, "ESCALATION_CONFIDENCE_THRESHOLD", 0.98):
        response = run_copilot_workflow(
            db=db,
            client_id="C-01",
            query="What is the CAGR for smart water meters in report R-101?",
            report_id="R-101"
        )
        assert isinstance(response, ChatResponse)
        assert response.escalated is True
        assert response.confidence < 0.98
        assert response.escalation_ticket is not None
        assert "analyst" in response.answer.lower()


# =====================================================================
# 2. Escalation Trigger: Missing Evidence
# =====================================================================

def test_escalation_triggers_on_missing_evidence(db):
    """
    Verify queries completely outside the available catalog escalate and explain what could not be verified.
    """
    # Asking for aerospace titanium alloys (completely absent from water/gas/purifier catalog)
    response = run_copilot_workflow(
        db=db,
        client_id="C-01",
        query="What is the market size of commercial aerospace titanium alloys in North America?"
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is True
    assert response.confidence <= 0.10
    assert response.escalation_ticket is not None
    assert "no verified research data" in response.answer.lower() or "outside" in response.answer.lower()
    assert "analyst" in response.answer.lower()


# =====================================================================
# 3. Escalation Trigger: Conflicting Sources Requiring Judgment
# =====================================================================

def test_escalation_triggers_on_conflicting_sources_judgment(db):
    """
    Verify that when authorized reports conflict (R-101 $4.21B vs R-102 $3.87B)
    and the user query demands picking or determining which figure is 'correct',
    the workflow escalates for analyst reconciliation rather than picking arbitrarily or averaging.
    """
    # Client C-01 has access to R-101 and R-102 (public)
    response = run_copilot_workflow(
        db=db,
        client_id="C-01",
        query="Which 2024 market size figure is correct between R-101 and R-102? Pick the right one."
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is True
    assert response.escalation_ticket is not None
    # Verified scope differences
    assert "4.21" in response.answer
    assert "3.87" in response.answer
    assert "what was verified" in response.answer.lower()
    assert "what remains uncertain" in response.answer.lower()
    assert "analyst" in response.answer.lower()


# =====================================================================
# 4. Escalation Trigger: Unresolved Calculation Assumptions
# =====================================================================

def test_escalation_triggers_on_unresolved_calculation_assumptions(db):
    """
    Verify queries requiring extrapolation beyond verified forecast windows escalate.
    """
    response = run_copilot_workflow(
        db=db,
        client_id="C-01",
        query="Project the smart water meter market size to 2038 using R-101",
        report_id="R-101"
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is True
    assert response.escalation_ticket is not None
    assert "forecast window" in response.answer.lower() or "extrapolation" in response.answer.lower()
    assert "analyst" in response.answer.lower()


# =====================================================================
# 5. Database Failures: Graceful Handling & No Ticket Fabrication
# =====================================================================

def test_escalation_database_failure_does_not_fabricate_ticket_id(db):
    """
    Verify that if the MySQL database operation fails during escalation creation,
    the workflow returns escalated=True, explains the situation to the client,
    and sets escalation_ticket=None WITHOUT fabricating a fake ticket ID.
    """
    with patch.object(EscalationService, "create_escalation", return_value={"ticket_id": None, "error": "Simulated DB down"}):
        response = run_copilot_workflow(
            db=db,
            client_id="C-01",
            query="Please escalate this request to a human analyst immediately for review."
        )

        assert isinstance(response, ChatResponse)
        assert response.escalated is True
        # Must NOT fabricate a fake ticket ID
        assert response.escalation_ticket is None
        # Response must not contain a fabricated ticket number like ESC-0000 or (Ticket: None)
        assert "(Ticket: None)" not in response.answer
        assert "analyst" in response.answer.lower()


# =====================================================================
# 6. Duplicate Submission Handling
# =====================================================================

def test_escalation_duplicate_submission_handling(db):
    """
    Verify that submitting the identical inquiry from the same client when an open
    ticket already exists reuses the existing ticket ID instead of duplicating records.
    """
    import uuid
    client_id = "C-01"
    query_text = f"Detailed inquiry regarding regional APAC market penetration anomalies - {uuid.uuid4().hex[:8]}"

    # First submission
    ticket_1 = EscalationService.create_escalation(
        client_id=client_id,
        query_text=query_text,
        reason="Manual audit request",
        db=db
    )
    assert ticket_1.get("ticket_id") is not None
    assert ticket_1.get("is_duplicate") is not True

    # Duplicate submission
    ticket_2 = EscalationService.create_escalation(
        client_id=client_id,
        query_text=query_text,
        reason="Manual audit request",
        db=db
    )
    assert ticket_2.get("ticket_id") == ticket_1.get("ticket_id")
    assert ticket_2.get("is_duplicate") is True


# =====================================================================
# 7. Persistence in MySQL
# =====================================================================

def test_successful_escalation_creation_persisted_in_mysql(db):
    """
    Verify that created tickets are truly persisted in the MySQL escalation_tickets table.
    """
    client_id = "C-02"
    query_text = "Request for specialized AMI smart water infrastructure validation."
    reason = "Infrastructure specialization review"

    ticket = EscalationService.create_escalation(
        client_id=client_id,
        query_text=query_text,
        reason=reason,
        priority="high",
        metadata={"custom_flag": "test_verification"},
        db=db
    )
    ticket_id = ticket.get("ticket_id")
    assert ticket_id is not None

    # Query directly from MySQL table using SQLAlchemy model
    persisted = db.query(EscalationTicket).filter(EscalationTicket.ticket_id == ticket_id).first()
    assert persisted is not None
    assert persisted.client_id == client_id
    assert persisted.query_text == query_text
    assert persisted.reason == reason
    assert persisted.priority == "high"
    assert persisted.status == "open"
    assert persisted.created_at is not None
    assert persisted.metadata_json.get("custom_flag") == "test_verification"


# =====================================================================
# 8. GET /escalations Authorized Listing & Filtering
# =====================================================================

def test_get_escalations_endpoint_authorized(client, db):
    """
    Verify GET /escalations returns tickets with authentication and filters.
    """
    # Create test ticket for C-01
    EscalationService.create_escalation(
        client_id="C-01",
        query_text="Filter verification ticket C-01",
        reason="Test filter",
        db=db
    )

    # Authorized call
    response = client.get("/escalations", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 1
    assert any(item["client_id"] == "C-01" for item in data["items"])

    # Filter by client_id=C-01
    filtered_res = client.get("/escalations?client_id=C-01", headers=AUTH_HEADERS)
    assert filtered_res.status_code == 200
    filtered_data = filtered_res.json()
    for item in filtered_data["items"]:
        assert item["client_id"] == "C-01"


# =====================================================================
# 9. GET /escalations Authorization & Security Rejections
# =====================================================================

def test_get_escalations_endpoint_unauthorized_access_rejected(client):
    """
    Verify GET /escalations rejects unauthenticated or unauthorized access.
    """
    # 1. Missing API Key
    res_no_auth = client.get("/escalations")
    assert res_no_auth.status_code == 401

    # 2. Invalid API Key
    res_bad_auth = client.get("/escalations", headers={"X-API-Key": "invalid-secret-key"})
    assert res_bad_auth.status_code == 401

    # 3. Nonexistent Client ID
    res_invalid_client = client.get("/escalations?client_id=C-UNKNOWN", headers=AUTH_HEADERS)
    assert res_invalid_client.status_code == 404


# =====================================================================
# 10. Normal Queries Do Not Escalate Unnecessarily
# =====================================================================

def test_normal_query_does_not_escalate_unnecessarily(db):
    """
    Verify that an ordinary factual query with verified evidence does NOT trigger escalation.
    """
    response = run_copilot_workflow(
        db=db,
        client_id="C-01",
        query="What is the CAGR for smart water meters in report R-101?",
        report_id="R-101"
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is False
    assert response.escalation_ticket is None
    assert response.confidence >= 0.85
    assert len(response.citations) >= 1
    assert "11.2%" in response.answer


# =====================================================================
# 11. Database Integrity: Preserve All Existing Records
# =====================================================================

def test_preserve_existing_database_records(db):
    """
    Verify that existing tables and records (clients, reports, market_metrics)
    remain completely intact, unaltered, and uncorrupted.
    """
    # Verify clients table
    clients_count = db.execute(text("SELECT count(*) FROM clients")).scalar()
    assert clients_count == 2
    c01 = db.execute(text("SELECT purchased_reports FROM clients WHERE id='C-01'")).scalar()
    assert "R-101" in c01 and "R-103" in c01

    # Verify reports table
    reports_count = db.execute(text("SELECT count(*) FROM reports")).scalar()
    assert reports_count == 3
    r101_access = db.execute(text("SELECT access FROM reports WHERE id='R-101'")).scalar()
    assert r101_access == "paid"
    r102_access = db.execute(text("SELECT access FROM reports WHERE id='R-102'")).scalar()
    assert r102_access == "public"

    # Verify market_metrics table
    metrics_count = db.execute(text("SELECT count(*) FROM market_metrics")).scalar()
    assert metrics_count == 24
