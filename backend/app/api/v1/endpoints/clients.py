"""
Client Management and Permissions Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.client_service import ClientService
from app.schemas.client import ClientRead, ClientAccessCheck
from app.security.masking import mask_sensitive_field

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: str, db: Session = Depends(get_db)):
    """Fetch client record by ID with masked contact email."""
    client = ClientService.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found.")
    
    # Return client with masked contact info
    masked_email = mask_sensitive_field("email", client.contact_email)
    return ClientRead(
        id=client.id,
        company=client.company,
        contact_email=masked_email,
        purchased_reports=client.purchased_reports
    )

@router.get("/{client_id}/access-check", response_model=ClientAccessCheck)
def check_client_report_access(
    client_id: str,
    report_id: str = Query(..., description="Report ID to check (e.g. R-101)"),
    db: Session = Depends(get_db)
):
    """Verify if a client has access to a specific report."""
    client = ClientService.get_client(db, client_id)
    has_access, reason = ClientService.check_report_access(db, client_id, report_id)
    return ClientAccessCheck(
        client_id=client_id,
        report_id=report_id,
        has_access=has_access,
        company=client.company if client else None,
        reason=reason
    )
