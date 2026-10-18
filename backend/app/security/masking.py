"""
Data Masking Utilities
Protects confidential client contacts and sensitive credentials in responses.
"""

from typing import Any

SENSITIVE_PATTERNS = {
    "password", "secret", "token", "hash", "key", "credential",
    "auth", "pwd", "ssn", "credit_card", "card", "cvv"
}
CONTACT_PATTERNS = {"email", "phone", "mobile", "contact"}

def mask_sensitive_field(field_name: str, value: Any) -> Any:
    """Mask sensitive attributes or emails."""
    if value is None:
        return None
    val_str = str(value)
    name_lower = field_name.lower()

    for pat in SENSITIVE_PATTERNS:
        if pat in name_lower:
            return "******** [MASKED]"

    for pat in CONTACT_PATTERNS:
        if pat in name_lower:
            if "@" in val_str:
                parts = val_str.split("@")
                masked_user = parts[0][:2] + "***" if len(parts[0]) > 2 else "***"
                return f"{masked_user}@{parts[1]}"
            elif len(val_str) > 4:
                return val_str[:2] + "****" + val_str[-2:]
            return "**** [MASKED]"

    return value
