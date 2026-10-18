from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class QueryRequest(BaseModel):
    query: str = Field(..., description="User question or research prompt")
    client_id: Optional[str] = Field(None, description="Client identifier for permission checking (e.g., C-01)")
    report_id: Optional[str] = Field(None, description="Optional target report id to restrict analysis")

class SourceCitation(BaseModel):
    report_id: Optional[str] = None
    title: Optional[str] = None
    metric: Optional[str] = None
    period: Optional[str] = None
    region: Optional[str] = None
    value: Optional[str] = None
    source_type: str = Field(default="relational_sql", description="relational_sql or vector_retrieval")

class QueryResponse(BaseModel):
    query: str
    client_id: Optional[str] = None
    answer: str
    access_granted: bool = True
    citations: List[SourceCitation] = []
    metadata: Dict[str, Any] = {}
