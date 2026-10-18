"""
Conversations and User Feedback Endpoints
Provides authenticated endpoints to list conversations, view historical messages,
and submit thumbs-up / thumbs-down ratings with strict cross-client isolation.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.auth import require_api_key, validate_client
from app.schemas.conversation import (
    ConversationsListResponse,
    ConversationHistoryResponse,
    ConversationItem,
    FeedbackRequest,
    FeedbackResponse
)
from app.services.conversation_service import ConversationService
from app.observability.logger import logger

router = APIRouter(tags=["Conversations & Feedback"])


@router.get(
    "/conversations",
    response_model=ConversationsListResponse,
    summary="List client conversations",
    description="Returns all conversation sessions owned by the authenticated client."
)
def list_conversations(
    client_id: str = Query(..., description="Client identifier (e.g. 'C-01')"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """List conversation sessions partitioned by client."""
    client = validate_client(client_id, db=db)
    convs = ConversationService.list_client_conversations(db=db, client_id=client.id, skip=skip, limit=limit)
    items = [
        ConversationItem(
            id=c.id,
            client_id=c.client_id,
            title=c.title or "New Conversation",
            created_at=c.created_at.isoformat() if c.created_at else None,
            updated_at=c.updated_at.isoformat() if c.updated_at else None
        )
        for c in convs
    ]
    return ConversationsListResponse(total=len(items), items=items)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history",
    description="Retrieves messages for a conversation session. Enforces strict client boundary."
)
def get_conversation(
    conversation_id: str,
    client_id: str = Query(..., description="Client identifier (e.g. 'C-01')"),
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """Retrieve full conversation history, enforcing that caller owns the session."""
    client = validate_client(client_id, db=db)
    data = ConversationService.get_conversation_history(
        db=db,
        conversation_id=conversation_id,
        client_id=client.id
    )
    return ConversationHistoryResponse(**data)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Submit user feedback on assistant message",
    description="Records thumbs-up or thumbs-down rating and optional comment. Handles duplicate submissions consistently."
)
def submit_feedback(
    request: FeedbackRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """Submit or update feedback for an assistant message with client validation."""
    client = validate_client(request.client_id, db=db)
    fb = ConversationService.record_feedback(
        db=db,
        client_id=client.id,
        message_id=request.message_id,
        rating=request.rating,
        comment=request.comment
    )
    return FeedbackResponse(
        status="success",
        message_id=fb.message_id,
        client_id=fb.client_id,
        rating=fb.rating,
        comment=fb.comment,
        recorded_at=fb.created_at.isoformat() if fb.created_at else ""
    )
