"""
PII Sanitizer - Privacy-First URL and Data Cleaning

This module provides comprehensive sanitization of Personally Identifiable
Information (PII) from URLs and data before sending to analytics.

PRIVACY GUARANTEE:
- NO screenshots or session recordings
- NO raw user data transmission
- ALL PII patterns are redacted before network requests

Patterns Detected:
- Email addresses
- UUIDs (v1-v5)
- JWT tokens (eyJ...)
- API keys (sk_, pk_, api_, key_)
- Phone numbers (international formats)
- Credit card patterns
- Long hex strings (32+ chars)
- Query parameter tokens
- Password reset tokens
- Session IDs

Usage:
    from shared.analytics.sanitizer import sanitize_url, sanitize_data
    
    # Sanitize a URL
    clean = sanitize_url("/user/john@example.com/reset?token=abc123")
    # Result: "/user/[REDACTED_EMAIL]/reset?token=[REDACTED_TOKEN]"
    
    # Sanitize event data
    clean_data = sanitize_data({"email": "user@test.com", "action": "login"})
    # Result: {"email": "[REDACTED_EMAIL]", "action": "login"}
"""

import re
from typing import Any, Dict, List, Optional, Pattern
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# =============================================================================
# REGEX PATTERNS FOR PII DETECTION
# =============================================================================

# Email addresses (RFC 5322 simplified)
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# UUIDs (v1-v5, with or without dashes)
UUID_PATTERN = re.compile(
    r'[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}',
    re.IGNORECASE
)

# JWT tokens (three base64 segments separated by dots)
JWT_PATTERN = re.compile(
    r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
    re.IGNORECASE
)

# API keys (common prefixes)
API_KEY_PATTERN = re.compile(
    r'(sk_|pk_|api_|key_|token_|secret_|bearer_)[a-zA-Z0-9_-]{10,}',
    re.IGNORECASE
)

# Phone numbers (international formats)
PHONE_PATTERN = re.compile(
    r'(\+?1?[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
)

# Credit card numbers (13-19 digits, with or without separators)
CREDIT_CARD_PATTERN = re.compile(
    r'\b(?:\d[-\s]?){13,19}\b'
)

# Long hex strings (32+ chars - likely tokens, hashes)
HEX_STRING_PATTERN = re.compile(
    r'[0-9a-f]{32,}',
    re.IGNORECASE
)

# Base64 encoded strings (20+ chars, likely tokens)
BASE64_PATTERN = re.compile(
    r'[A-Za-z0-9+/]{20,}={0,2}'
)

# Query parameter patterns that often contain sensitive data
SENSITIVE_PARAMS = {
    'token', 'key', 'apikey', 'api_key', 'secret', 'password', 'pwd',
    'auth', 'authorization', 'access_token', 'refresh_token', 'id_token',
    'session', 'session_id', 'sessionid', 'csrf', 'nonce', 'code',
    'verification', 'verify', 'reset', 'confirm', 'activation'
}


# =============================================================================
# REPLACEMENT STRINGS
# =============================================================================

REDACTED_EMAIL = '[REDACTED_EMAIL]'
REDACTED_UUID = '[REDACTED_UUID]'
REDACTED_TOKEN = '[REDACTED_TOKEN]'
REDACTED_KEY = '[REDACTED_KEY]'
REDACTED_PHONE = '[REDACTED_PHONE]'
REDACTED_CARD = '[REDACTED_CARD]'
REDACTED_HEX = '[REDACTED_HEX]'
REDACTED_VALUE = '[REDACTED]'


# =============================================================================
# SANITIZATION FUNCTIONS
# =============================================================================

def sanitize_string(value: str, config: Optional[Dict] = None) -> str:
    """
    Sanitize a string by replacing all PII patterns.
    
    Args:
        value: The string to sanitize
        config: Optional configuration dict with enabled patterns
        
    Returns:
        Sanitized string with PII replaced by redaction markers
    """
    if not value or not isinstance(value, str):
        return value or ''
    
    # Default config - all patterns enabled
    cfg = config or {}
    
    result = value
    
    # Order matters - more specific patterns first
    
    # JWT tokens (before general base64)
    if cfg.get('sanitize_tokens', True):
        result = JWT_PATTERN.sub(REDACTED_TOKEN, result)
    
    # API keys
    if cfg.get('sanitize_api_keys', True):
        result = API_KEY_PATTERN.sub(REDACTED_KEY, result)
    
    # Emails
    if cfg.get('sanitize_emails', True):
        result = EMAIL_PATTERN.sub(REDACTED_EMAIL, result)
    
    # UUIDs
    if cfg.get('sanitize_uuids', True):
        result = UUID_PATTERN.sub(REDACTED_UUID, result)
    
    # Phone numbers
    if cfg.get('sanitize_phones', True):
        result = PHONE_PATTERN.sub(REDACTED_PHONE, result)
    
    # Credit cards
    if cfg.get('sanitize_credit_cards', True):
        result = CREDIT_CARD_PATTERN.sub(REDACTED_CARD, result)
    
    # Long hex strings (after UUIDs to avoid double-redaction)
    if cfg.get('sanitize_hex_strings', True):
        result = HEX_STRING_PATTERN.sub(REDACTED_HEX, result)
    
    # Custom patterns
    for pattern in cfg.get('custom_patterns', []):
        try:
            result = re.sub(pattern, REDACTED_VALUE, result)
        except re.error:
            pass  # Invalid pattern, skip
    
    return result


def sanitize_url(url: str, config: Optional[Dict] = None) -> str:
    """
    Sanitize a URL by removing PII from path and query parameters.
    
    Args:
        url: The URL to sanitize
        config: Optional configuration dict
        
    Returns:
        Sanitized URL safe for analytics
        
    Example:
        >>> sanitize_url("/user/john@example.com/reset?token=abc123")
        '/user/[REDACTED_EMAIL]/reset?token=[REDACTED_TOKEN]'
    """
    if not url:
        return '/'
    
    try:
        # Handle relative URLs
        if not url.startswith(('http://', 'https://')):
            # Add temporary scheme for parsing
            parsed = urlparse('http://temp' + (url if url.startswith('/') else '/' + url))
            is_relative = True
        else:
            parsed = urlparse(url)
            is_relative = False
        
        # Sanitize path
        clean_path = sanitize_string(parsed.path, config)
        
        # Sanitize query parameters
        if parsed.query:
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            clean_params = {}
            
            for key, values in query_params.items():
                # Check if this is a sensitive parameter
                if key.lower() in SENSITIVE_PARAMS:
                    clean_params[key] = [REDACTED_VALUE]
                else:
                    # Sanitize the values
                    clean_params[key] = [sanitize_string(v, config) for v in values]
            
            # Rebuild query string
            clean_query = urlencode(clean_params, doseq=True)
        else:
            clean_query = ''
        
        # Rebuild URL
        if is_relative:
            if clean_query:
                return f"{clean_path}?{clean_query}"
            return clean_path
        else:
            clean_parsed = parsed._replace(path=clean_path, query=clean_query)
            return urlunparse(clean_parsed)
            
    except Exception:
        # If parsing fails, just sanitize the whole string
        return sanitize_string(url, config)


def sanitize_data(data: Any, config: Optional[Dict] = None, 
                  sensitive_fields: Optional[List[str]] = None) -> Any:
    """
    Recursively sanitize a data structure (dict, list, or primitive).
    
    Args:
        data: The data to sanitize (dict, list, str, etc.)
        config: Optional configuration dict
        sensitive_fields: List of field names to always redact
        
    Returns:
        Sanitized data structure
        
    Example:
        >>> sanitize_data({"email": "user@test.com", "action": "login"})
        {"email": "[REDACTED_EMAIL]", "action": "login"}
    """
    # Default sensitive fields
    default_sensitive = {
        'password', 'token', 'secret', 'api_key', 'apikey', 'authorization',
        'credit_card', 'card_number', 'cvv', 'ssn', 'access_token', 
        'refresh_token', 'private_key', 'secret_key'
    }
    
    sensitive = set(f.lower() for f in (sensitive_fields or []))
    sensitive.update(default_sensitive)
    
    if data is None:
        return None
    
    if isinstance(data, str):
        return sanitize_string(data, config)
    
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Check if field name is sensitive
            if key.lower() in sensitive:
                result[key] = REDACTED_VALUE
            else:
                result[key] = sanitize_data(value, config, sensitive_fields)
        return result
    
    if isinstance(data, (list, tuple)):
        return type(data)(sanitize_data(item, config, sensitive_fields) for item in data)
    
    # Numbers, booleans, etc. - return as-is
    return data


def is_pii_detected(value: str) -> bool:
    """
    Check if a string contains any PII patterns.
    
    Args:
        value: String to check
        
    Returns:
        True if PII is detected, False otherwise
    """
    if not value or not isinstance(value, str):
        return False
    
    patterns = [
        EMAIL_PATTERN,
        UUID_PATTERN,
        JWT_PATTERN,
        API_KEY_PATTERN,
        PHONE_PATTERN,
        CREDIT_CARD_PATTERN,
    ]
    
    return any(pattern.search(value) for pattern in patterns)


def get_pii_types(value: str) -> List[str]:
    """
    Get list of PII types detected in a string.
    
    Args:
        value: String to check
        
    Returns:
        List of detected PII type names
    """
    if not value or not isinstance(value, str):
        return []
    
    detected = []
    
    if EMAIL_PATTERN.search(value):
        detected.append('email')
    if UUID_PATTERN.search(value):
        detected.append('uuid')
    if JWT_PATTERN.search(value):
        detected.append('jwt_token')
    if API_KEY_PATTERN.search(value):
        detected.append('api_key')
    if PHONE_PATTERN.search(value):
        detected.append('phone')
    if CREDIT_CARD_PATTERN.search(value):
        detected.append('credit_card')
    if HEX_STRING_PATTERN.search(value):
        detected.append('hex_string')
    
    return detected
