"""
Pydantic Schemas for Conversation Persistence & Feedback Endpoints
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    client_id: str = Field(..., description="Client identifier (e.g. 'C-01')")
    message_id: int = Field(..., description="Target assistant message ID")
    rating: str = Field(..., description="Feedback rating: 'thumbs_up' or 'thumbs_down'")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional user comment")


class FeedbackResponse(BaseModel):
    status: str = "success"
    message_id: int
    client_id: str
    rating: str
    comment: Optional[str] = None
    recorded_at: str


class MessageItem(BaseModel):
    id: int
    sender: str
    content: str
    citations: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    derived_values: Dict[str, Any] = {}
    confidence: Optional[float] = None
    escalated: bool = False
    escalation_ticket: Optional[str] = None
    created_at: Optional[str] = None
    feedback_rating: Optional[str] = None
    feedback_comment: Optional[str] = None


class ConversationItem(BaseModel):
    id: str
    client_id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    id: str
    client_id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    messages: List[MessageItem] = []


class ConversationsListResponse(BaseModel):
    total: int
    items: List[ConversationItem]
