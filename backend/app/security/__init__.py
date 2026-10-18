"""
Security Package
"""

from .auth import require_api_key, validate_client
from .masking import mask_sensitive_field

# Backward-compatible aliases
verify_api_key = require_api_key
get_current_client_id = validate_client

__all__ = [
    "require_api_key",
    "validate_client",
    "verify_api_key",
    "get_current_client_id",
    "mask_sensitive_field"
]
