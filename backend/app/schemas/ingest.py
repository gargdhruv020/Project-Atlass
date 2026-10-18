"""
Pydantic Schemas for /ingest Endpoint
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class IngestRequest(BaseModel):
    report_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Target report identifier (e.g. 'R-101', 'R-104')"
    )
    title: Optional[str] = Field(
        None,
        max_length=255,
        description="Report title"
    )
    content: Optional[str] = Field(
        None,
        description="Direct document text content to ingest into vector storage"
    )
    file_path: Optional[str] = Field(
        None,
        description="Relative or absolute path to document file under documents/"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional additional metadata tags for vector chunks"
    )

class IngestResponse(BaseModel):
    status: str = "success"
    report_id: str
    chunks_ingested: int
    collection: str
    message: str
