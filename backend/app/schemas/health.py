"""
Pydantic Schemas for /health Endpoint
"""

from typing import Dict, Any
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    project: str
    version: str
    dependencies: Dict[str, Any]
