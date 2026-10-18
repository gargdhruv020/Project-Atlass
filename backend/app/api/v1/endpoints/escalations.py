"""
Escalations Endpoint: GET /escalations
Retrieves analyst escalation tickets for authorized users.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.auth import require_api_key, validate_client
from app.schemas.escalation import EscalationsResponse, EscalationRecord
from app.services.escalation_service import EscalationService

router = APIRouter(tags=["Escalations"])

@router.get(
    "/escalations",
    response_model=EscalationsResponse,
    summary="List analyst escalation tickets",
    description="Returns unresolved and historical analyst tickets for authorized callers."
)
async def list_escalations_endpoint(
    client_id: Optional[str] = Query(None, description="Filter by client ID (e.g. 'C-01')"),
    status: Optional[str] = Query(None, description="Filter by ticket status ('open', 'resolved')"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Retrieves escalation records with authentication and optional client validation.
    """
    if client_id:
        validate_client(client_id, db=db)

    items = EscalationService.list_escalations(
        client_id=client_id,
        status=status,
        skip=skip,
        limit=limit
    )
    total = EscalationService.count_escalations(client_id=client_id)

    return EscalationsResponse(
        total=total,
        items=[EscalationRecord(**item) for item in items]
    )
