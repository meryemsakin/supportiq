"""
Validation Utilities

Common validation functions.
"""

import re
from typing import Optional
from uuid import UUID


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid email format
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_uuid(value: str) -> bool:
    """
    Validate UUID format.
    
    Args:
        value: String to validate as UUID
        
    Returns:
        bool: True if valid UUID
    """
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False


def validate_priority(priority: int) -> bool:
    """
    Validate priority value.
    
    Args:
        priority: Priority value to validate
        
    Returns:
        bool: True if valid (1-5)
    """
    return isinstance(priority, int) and 1 <= priority <= 5


def validate_language_code(code: str) -> bool:
    """
    Validate language code (ISO 639-1).
    
    Args:
        code: Language code to validate
        
    Returns:
        bool: True if valid
    """
    valid_codes = {'tr', 'en', 'de', 'fr', 'es', 'it', 'pt', 'nl', 'ru', 'ar', 'zh', 'ja', 'ko'}
    return code.lower() in valid_codes


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not value:
        return ""
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Truncate
    if len(value) > max_length:
        value = value[:max_length]
    
    return value.strip()


def validate_webhook_payload(payload: dict, required_fields: list) -> tuple[bool, Optional[str]]:
    """
    Validate webhook payload has required fields.
    
    Args:
        payload: Webhook payload dictionary
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"
    
    missing = [f for f in required_fields if f not in payload]
    
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    return True, None
