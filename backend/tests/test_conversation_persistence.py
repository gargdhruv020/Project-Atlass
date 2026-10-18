"""
Conversation Persistence and User Feedback Test Suite
Verifies message history recording, client authorization boundaries,
thumbs-up/thumbs-down feedback, repeated feedback consistency, and failure handling.
"""

import uuid
import pytest
from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import ChatMessage
from app.models.feedback import MessageFeedback


def test_conversation_and_message_persistence_flow(client, db):
    """
    Verify that querying POST /chat automatically creates a conversation record,
    associates it with the client, and stores both user query and assistant response
    with complete research metadata (citations, confidence, etc.).
    """
    headers = {"x-api-key": settings.API_KEY}
    conv_id = str(uuid.uuid4())
    payload = {
        "client_id": "C-01",
        "conversation_id": conv_id,
        "query": "What is the 2024 smart water meter market size in R-101?"
    }

    response = client.post("/chat", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["conversation_id"] == conv_id
    assert "message_id" in data
    assert data["message_id"] is not None
    assistant_msg_id = data["message_id"]

    # Verify MySQL database persistence directly
    conv_row = db.query(Conversation).filter(Conversation.id == conv_id).first()
    assert conv_row is not None
    assert conv_row.client_id == "C-01"
    assert len(conv_row.title) > 0

    # Verify user message in MySQL
    user_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv_id, ChatMessage.sender == "user")
        .first()
    )
    assert user_msg is not None
    assert user_msg.client_id == "C-01"
    assert "2024 smart water meter market size" in user_msg.content

    # Verify assistant message in MySQL
    asst_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.id == assistant_msg_id)
        .first()
    )
    assert asst_msg is not None
    assert asst_msg.sender == "assistant"
    assert asst_msg.client_id == "C-01"
    assert asst_msg.citations is not None
    assert len(asst_msg.citations) > 0
    assert asst_msg.confidence is not None


def test_cross_client_conversation_isolation(client):
    """
    Verify that Client C-02 CANNOT access or read Client C-01's conversation history.
    Strictly enforces 403 Forbidden cross-client boundary.
    """
    headers = {"x-api-key": settings.API_KEY}
    c01_conv_id = str(uuid.uuid4())

    # 1. C-01 creates a conversation
    chat_resp = client.post(
        "/chat",
        json={
            "client_id": "C-01",
            "conversation_id": c01_conv_id,
            "query": "What is the CAGR in R-101?"
        },
        headers=headers
    )
    assert chat_resp.status_code == 200

    # 2. C-02 attempts to view C-01's conversation
    unauth_view = client.get(
        f"/conversations/{c01_conv_id}?client_id=C-02",
        headers=headers
    )
    assert unauth_view.status_code == 403
    assert "access denied" in unauth_view.json()["detail"].lower()

    # 3. C-02 listing conversations should NOT see C-01's conversation
    c02_list = client.get("/conversations?client_id=C-02", headers=headers)
    assert c02_list.status_code == 200
    c02_conv_ids = [item["id"] for item in c02_list.json()["items"]]
    assert c01_conv_id not in c02_conv_ids

    # 4. C-01 listing conversations DOES see their own conversation
    c01_list = client.get("/conversations?client_id=C-01", headers=headers)
    assert c01_list.status_code == 200
    c01_conv_ids = [item["id"] for item in c01_list.json()["items"]]
    assert c01_conv_id in c01_conv_ids


def test_user_feedback_submission_and_duplicate_handling(client, db):
    """
    Verify thumbs-up and thumbs-down feedback submission, database recording,
    and consistent handling of repeated feedback submissions (UPSERT).
    """
    headers = {"x-api-key": settings.API_KEY}
    conv_id = str(uuid.uuid4())

    # Create message to rate
    chat_resp = client.post(
        "/chat",
        json={
            "client_id": "C-01",
            "conversation_id": conv_id,
            "query": "Tell me about R-103 purifier market."
        },
        headers=headers
    )
    assert chat_resp.status_code == 200
    msg_id = chat_resp.json()["message_id"]
    assert msg_id is not None

    # 1. Submit initial thumbs_up feedback
    fb1 = client.post(
        "/feedback",
        json={
            "client_id": "C-01",
            "message_id": msg_id,
            "rating": "thumbs_up",
            "comment": "Accurate and clear numbers"
        },
        headers=headers
    )
    assert fb1.status_code == 200
    data1 = fb1.json()
    assert data1["status"] == "success"
    assert data1["rating"] == "thumbs_up"
    assert data1["comment"] == "Accurate and clear numbers"

    # Verify row in MySQL
    fb_row = (
        db.query(MessageFeedback)
        .filter(MessageFeedback.message_id == msg_id, MessageFeedback.client_id == "C-01")
        .first()
    )
    assert fb_row is not None
    assert fb_row.rating == "thumbs_up"

    # 2. Repeated feedback submission: change rating to thumbs_down with new comment
    fb2 = client.post(
        "/feedback",
        json={
            "client_id": "C-01",
            "message_id": msg_id,
            "rating": "thumbs_down",
            "comment": "Changed my mind, need more detail"
        },
        headers=headers
    )
    assert fb2.status_code == 200
    data2 = fb2.json()
    assert data2["rating"] == "thumbs_down"
    assert data2["comment"] == "Changed my mind, need more detail"

    # Verify row was updated in MySQL without creating duplicates
    db.commit()
    all_fbs = (
        db.query(MessageFeedback)
        .filter(MessageFeedback.message_id == msg_id, MessageFeedback.client_id == "C-01")
        .all()
    )
    assert len(all_fbs) == 1
    assert all_fbs[0].rating == "thumbs_down"


def test_cross_client_feedback_rejected(client):
    """
    Verify that Client C-02 CANNOT submit feedback on Client C-01's message.
    """
    headers = {"x-api-key": settings.API_KEY}

    # C-01 creates message
    chat_resp = client.post(
        "/chat",
        json={
            "client_id": "C-01",
            "query": "What is R-101 market size?"
        },
        headers=headers
    )
    assert chat_resp.status_code == 200
    msg_id = chat_resp.json()["message_id"]

    # C-02 tries to rate C-01's message
    unauth_fb = client.post(
        "/feedback",
        json={
            "client_id": "C-02",
            "message_id": msg_id,
            "rating": "thumbs_up"
        },
        headers=headers
    )
    assert unauth_fb.status_code == 403
    assert "access denied" in unauth_fb.json()["detail"].lower()


def test_invalid_feedback_parameters(client):
    """
    Verify validation handles invalid rating and non-existent message IDs.
    """
    headers = {"x-api-key": settings.API_KEY}

    # Invalid rating enum
    resp = client.post(
        "/feedback",
        json={
            "client_id": "C-01",
            "message_id": 1,
            "rating": "super_helpful"
        },
        headers=headers
    )
    assert resp.status_code == 400

    # Non-existent message ID
    resp2 = client.post(
        "/feedback",
        json={
            "client_id": "C-01",
            "message_id": 9999999,
            "rating": "thumbs_up"
        },
        headers=headers
    )
    assert resp2.status_code == 404


def test_zero_credential_leak_in_conversation_records(client, db):
    """
    Verify that API keys and database passwords are never stored in conversation records.
    """
    headers = {"x-api-key": settings.API_KEY}
    conv_id = str(uuid.uuid4())

    client.post(
        "/chat",
        json={
            "client_id": "C-01",
            "conversation_id": conv_id,
            "query": "Check system status"
        },
        headers=headers
    )

    conv_data = client.get(f"/conversations/{conv_id}?client_id=C-01", headers=headers).json()
    raw_str = str(conv_data)
    assert settings.DB_PASSWORD not in raw_str
    assert settings.API_KEY not in raw_str
    assert settings.SECRET_KEY not in raw_str
