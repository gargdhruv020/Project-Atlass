"""
Pydantic Schemas for /chat Endpoint
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    client_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Client identifier (e.g., 'C-01', 'C-02')"
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Market research query prompt"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID for multi-turn sessions"
    )
    report_id: Optional[str] = Field(
        None,
        description="Optional report ID to restrict analysis scope (e.g., 'R-101')"
    )

class CitationItem(BaseModel):
    report_id: Optional[str] = None
    title: Optional[str] = None
    metric: Optional[str] = None
    period: Optional[str] = None
    region: Optional[str] = None
    value: Optional[str] = None
    page: Optional[int] = None
    source_type: str = Field(default="relational_sql", description="relational_sql or vector_retrieval")
    text_snippet: Optional[str] = None

class ConflictItem(BaseModel):
    metric: str
    description: str
    sources: List[str]

class ChatResponse(BaseModel):
    answer: str
    citations: List[CitationItem]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    conflicts: List[ConflictItem] = []
    derived_values: Dict[str, Any] = {}
    escalated: bool = False
    client_id: str
    conversation_id: Optional[str] = None
    escalation_ticket: Optional[str] = None
