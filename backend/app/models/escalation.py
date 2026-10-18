"""
SQLAlchemy Model for Escalation Tickets
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base

class EscalationTicket(Base):
    __tablename__ = "escalation_tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(50), unique=True, nullable=False, index=True)
    client_id = Column(String(10), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="open", index=True)
    priority = Column(String(20), nullable=False, default="medium")
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "client_id": self.client_id,
            "query_text": self.query_text,
            "reason": self.reason,
            "status": self.status,
            "priority": self.priority,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
