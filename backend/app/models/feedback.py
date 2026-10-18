"""
MessageFeedback Model for Project Atlas
Stores user thumbs-up and thumbs-down ratings with optional comments.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class MessageFeedback(Base):
    __tablename__ = "message_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(String(36), nullable=False)
    client_id = Column(String(10), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(String(20), nullable=False)  # 'thumbs_up' or 'thumbs_down'
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("message_id", "client_id", name="uk_message_client_feedback"),
    )

    # Relationships
    message = relationship("ChatMessage", back_populates="feedbacks")
