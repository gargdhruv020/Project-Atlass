"""
Pydantic Schemas for /escalations Endpoint
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class EscalationRecord(BaseModel):
    ticket_id: str
    client_id: str
    query_text: str
    status: str = "open"
    priority: str = "medium"
    reason: Optional[str] = None
    created_at: str
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    updated_at: Optional[str] = None

class EscalationsResponse(BaseModel):
    total: int
    items: List[EscalationRecord]
