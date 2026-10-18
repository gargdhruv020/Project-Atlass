"""
Authentication & Access Control
Validates API keys and client context for API requests.
"""

from typing import Optional
from fastapi import Header, HTTPException, status
from app.core.config import settings

def get_current_client_id(
    x_client_id: Optional[str] = Header(None, description="Optional Client ID header (e.g., C-01)")
) -> Optional[str]:
    """Extract and sanitize client ID from request headers."""
    if x_client_id:
        return x_client_id.strip()
    return None

def verify_api_key(
    x_api_key: Optional[str] = Header(None, description="Optional API Key header")
) -> bool:
    """Validate internal API key if configured."""
    if settings.SECRET_KEY and settings.SECRET_KEY != "atlas-insecure-secret-key-change-in-production":
        if x_api_key != settings.SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key"
            )
    return True
