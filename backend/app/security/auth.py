"""
Authentication & Access Control
Validates API keys and client context for API requests.
"""

from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.client_service import ClientService
from app.models.client import Client

def require_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="API Key header"),
    authorization: Optional[str] = Header(None, alias="Authorization", description="Bearer token header")
) -> str:
    """
    Validate caller's API key from either X-API-Key or Authorization header.
    Returns the validated key or raises 401 Unauthorized.
    """
    provided_key = None
    if x_api_key:
        provided_key = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization[7:].strip()

    valid_keys = {settings.API_KEY, settings.SECRET_KEY}
    # Exclude insecure default placeholder if custom key configured
    if not provided_key or provided_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Please provide a valid 'X-API-Key' or 'Authorization: Bearer <key>' header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return provided_key

def validate_client(
    client_id: str,
    db: Session = Depends(get_db)
) -> Client:
    """
    Validate that client_id exists in MySQL database.
    Raises 404 Not Found if client is unknown.
    """
    if not client_id or not client_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id is required and cannot be empty."
        )

    client = ClientService.get_client(db, client_id.strip())
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' not found."
        )

    return client
