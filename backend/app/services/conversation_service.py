"""
Conversation & Feedback Service for Project Atlas
Handles multi-turn conversation persistence, message archival with structured AI metadata,
strict client authorization partitioning, transactional feedback recording, and duplicate resolution.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status


def _now_utc() -> datetime:
    """Return timezone-naive UTC timestamp for MySQL compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from app.models.conversation import Conversation
from app.models.message import ChatMessage
from app.models.feedback import MessageFeedback
from app.models.client import Client
from app.observability.logger import logger


class ConversationService:
    """
    Authoritative service managing conversation lifecycle, message persistence,
    client boundary enforcement, and user feedback in MySQL.
    """

    @staticmethod
    def get_or_create_conversation(
        db: Session,
        client_id: str,
        conversation_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Conversation:
        """
        Retrieves existing conversation or creates a new one.
        Strictly enforces that the requesting client owns the conversation.
        """
        if conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                if conv.client_id != client_id:
                    logger.warning(
                        f"SECURITY ALERT: Client '{client_id}' attempted to access "
                        f"conversation '{conversation_id}' owned by client '{conv.client_id}'."
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Cannot access conversations belonging to another client."
                    )
                return conv

        # Use provided conversation_id or generate new UUID
        target_id = conversation_id if conversation_id else str(uuid.uuid4())
        initial_title = title or "New Research Session"
        
        try:
            new_conv = Conversation(
                id=target_id,
                client_id=client_id,
                title=initial_title,
                created_at=_now_utc(),
                updated_at=_now_utc()
            )
            db.add(new_conv)
            db.commit()
            db.refresh(new_conv)
            logger.info(f"Created new conversation '{target_id}' for client '{client_id}'")
            return new_conv
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to create conversation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while initializing conversation session."
            )

    @staticmethod
    def save_message(
        db: Session,
        conversation_id: str,
        client_id: str,
        sender: str,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        conflicts: Optional[List[Dict[str, Any]]] = None,
        derived_values: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        escalated: bool = False,
        escalation_ticket: Optional[str] = None
    ) -> ChatMessage:
        """
        Saves user or assistant message with structured research metadata within a database transaction.
        Enforces client ownership and updates conversation timestamp and title.
        """
        # Validate sender
        if sender not in ("user", "assistant"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sender '{sender}'. Must be 'user' or 'assistant'."
            )

        # Verify conversation ownership
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            conv = ConversationService.get_or_create_conversation(db, client_id, conversation_id)
        elif conv.client_id != client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot save message to another client's conversation."
            )

        try:
            # Update title from first user query
            if sender == "user" and (conv.title == "New Research Session" or not conv.title):
                clean_q = content.strip().replace("\n", " ")
                short_title = clean_q[:42] + ("..." if len(clean_q) > 42 else "")
                conv.title = short_title

            conv.updated_at = _now_utc()

            msg = ChatMessage(
                conversation_id=conversation_id,
                client_id=client_id,
                sender=sender,
                content=content,
                citations=citations or [],
                conflicts=conflicts or [],
                derived_values=derived_values or {},
                confidence=confidence,
                escalated=escalated,
                escalation_ticket=escalation_ticket,
                created_at=_now_utc()
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)
            return msg
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to persist chat message: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while saving message to conversation history."
            )

    @staticmethod
    def list_client_conversations(
        db: Session,
        client_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Conversation]:
        """
        Lists conversations strictly owned by the specified client.
        Guarantees isolation between clients.
        """
        return (
            db.query(Conversation)
            .filter(Conversation.client_id == client_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_conversation_history(
        db: Session,
        conversation_id: str,
        client_id: str
    ) -> Dict[str, Any]:
        """
        Retrieves full conversation with message history.
        Enforces authorization: returns 403 if requested by non-owner.
        """
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found."
            )

        if conv.client_id != client_id:
            logger.warning(
                f"SECURITY ALERT: Client '{client_id}' blocked from viewing conversation "
                f"'{conversation_id}' owned by '{conv.client_id}'."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view this conversation."
            )

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )

        # Retrieve user feedbacks for messages in this conversation
        feedbacks = (
            db.query(MessageFeedback)
            .filter(MessageFeedback.conversation_id == conversation_id, MessageFeedback.client_id == client_id)
            .all()
        )
        fb_map = {fb.message_id: {"rating": fb.rating, "comment": fb.comment} for fb in feedbacks}

        msg_list = []
        for m in messages:
            fb_info = fb_map.get(m.id, {})
            msg_list.append({
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "citations": m.citations or [],
                "conflicts": m.conflicts or [],
                "derived_values": m.derived_values or {},
                "confidence": m.confidence,
                "escalated": m.escalated,
                "escalation_ticket": m.escalation_ticket,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "feedback_rating": fb_info.get("rating"),
                "feedback_comment": fb_info.get("comment")
            })

        return {
            "id": conv.id,
            "client_id": conv.client_id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            "messages": msg_list
        }

    @staticmethod
    def record_feedback(
        db: Session,
        client_id: str,
        message_id: int,
        rating: str,
        comment: Optional[str] = None
    ) -> MessageFeedback:
        """
        Records or updates user feedback (thumbs_up / thumbs_down) for an assistant message.
        Validates client ownership and handles repeated feedback submissions consistently.
        """
        # 1. Validate rating value
        clean_rating = rating.strip().lower()
        if clean_rating not in ("thumbs_up", "thumbs_down"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid rating. Must be 'thumbs_up' or 'thumbs_down'."
            )

        # 2. Locate message and verify ownership
        msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message with ID {message_id} not found."
            )

        if msg.client_id != client_id:
            logger.warning(
                f"SECURITY ALERT: Client '{client_id}' attempted to rate message {message_id} "
                f"owned by client '{msg.client_id}'."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot submit feedback on another client's message."
            )

        # 3. Transactional UPSERT (consistent duplicate submission handling)
        try:
            existing = (
                db.query(MessageFeedback)
                .filter(MessageFeedback.message_id == message_id, MessageFeedback.client_id == client_id)
                .first()
            )

            if existing:
                existing.rating = clean_rating
                existing.comment = comment.strip() if comment else None
                existing.created_at = _now_utc()
                db.commit()
                db.refresh(existing)
                logger.info(f"Updated feedback for message {message_id} by client '{client_id}' -> {clean_rating}")
                return existing
            else:
                fb = MessageFeedback(
                    message_id=message_id,
                    conversation_id=msg.conversation_id,
                    client_id=client_id,
                    rating=clean_rating,
                    comment=comment.strip() if comment else None,
                    created_at=_now_utc()
                )
                db.add(fb)
                db.commit()
                db.refresh(fb)
                logger.info(f"Recorded new feedback for message {message_id} by client '{client_id}' -> {clean_rating}")
                return fb
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to record message feedback: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while saving feedback."
            )
