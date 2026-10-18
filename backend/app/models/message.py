"""
ChatMessage Model for Project Atlas
Stores individual user queries and assistant answers with structured metadata.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(String(10), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)
    conflicts = Column(JSON, nullable=True)
    derived_values = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    escalated = Column(Boolean, default=False)
    escalation_ticket = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    feedbacks = relationship("MessageFeedback", back_populates="message", cascade="all, delete-orphan")
