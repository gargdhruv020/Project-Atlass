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
    report_title: Optional[str] = None
    metric: Optional[str] = None
    period: Optional[str] = None
    region: Optional[str] = None
    value: Optional[str] = None
    page: Optional[int] = None
    claim: Optional[str] = None
    supporting_excerpt: Optional[str] = None
    source_type: str = Field(
        default="relational_sql",
        description="Source type: relational_sql, vector_retrieval, or calculation_input"
    )
    text_snippet: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.report_title and not self.title:
            self.title = self.report_title
        elif self.title and not self.report_title:
            self.report_title = self.title

        if self.supporting_excerpt and not self.text_snippet:
            self.text_snippet = self.supporting_excerpt
        elif self.text_snippet and not self.supporting_excerpt:
            self.supporting_excerpt = self.text_snippet

        if self.text_snippet and not self.claim:
            self.claim = self.text_snippet
        elif self.claim and not self.text_snippet:
            self.text_snippet = self.claim
            self.supporting_excerpt = self.claim


class ConflictItem(BaseModel):
    metric: str
    description: str
    sources: List[str]
    scope_differences: Dict[str, str] = Field(default_factory=dict)
    unresolved: bool = True

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
