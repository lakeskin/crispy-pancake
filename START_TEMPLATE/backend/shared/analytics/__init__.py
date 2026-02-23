"""
Umami Analytics Module - Privacy-First Analytics for Python Applications

This module provides a production-ready, privacy-focused analytics integration
with Umami Analytics. It's designed to be reusable, configurable, and safe.

PRIVACY GUARANTEE:
- This module ONLY sends text-based events and metrics
- NO screenshots, session recordings, or DOM captures
- ALL PII is automatically sanitized before transmission
- URLs are cleaned of emails, tokens, and sensitive data

Quick Start:
    from shared.analytics import get_analytics, track_event, track_page_view
    
    # Option 1: Use the factory function
    analytics = get_analytics('my_app')
    analytics.track_event('signup', {'plan': 'pro'})
    analytics.track_page_view('/dashboard')
    
    # Option 2: Use convenience functions
    track_event('button_click', {'button': 'submit'})
    track_page_view('/profile')
    
    # Option 3: Flask integration
    from flask import Flask
    app = Flask(__name__)
    analytics.init_flask(app)  # Auto-tracks all requests

Environment Variables:
    UMAMI_WEBSITE_ID  - Your Umami website ID (required)
    UMAMI_API_URL     - API endpoint (default: https://cloud.umami.is)
    UMAMI_API_KEY     - API key for authenticated requests
    UMAMI_ENABLED     - Enable/disable (true/false)
    UMAMI_DEBUG       - Debug mode (true/false)

Configuration:
    See shared/analytics/config.yaml for full configuration options.
    Environment-specific settings are applied automatically.

Privacy Utilities:
    from shared.analytics import sanitize_url, sanitize_data, is_pii_detected
    
    # Clean a URL
    clean = sanitize_url('/user/john@example.com/reset?token=abc')
    # Result: '/user/[REDACTED_EMAIL]/reset?token=[REDACTED]'
    
    # Check for PII
    if is_pii_detected(user_input):
        print("Warning: PII detected!")
"""

# Core analytics
from .umami import (
    UmamiAnalytics,
    get_analytics,
    track_event,
    track_page_view,
    track_route,
)

# Privacy utilities
from .sanitizer import (
    sanitize_url,
    sanitize_data,
    sanitize_string,
    is_pii_detected,
    get_pii_types,
    # Redaction constants
    REDACTED_EMAIL,
    REDACTED_UUID,
    REDACTED_TOKEN,
    REDACTED_KEY,
    REDACTED_PHONE,
    REDACTED_CARD,
    REDACTED_HEX,
    REDACTED_VALUE,
)

__all__ = [
    # Core
    'UmamiAnalytics',
    'get_analytics',
    'track_event',
    'track_page_view',
    'track_route',
    
    # Sanitization
    'sanitize_url',
    'sanitize_data',
    'sanitize_string',
    'is_pii_detected',
    'get_pii_types',
    
    # Constants
    'REDACTED_EMAIL',
    'REDACTED_UUID',
    'REDACTED_TOKEN',
    'REDACTED_KEY',
    'REDACTED_PHONE',
    'REDACTED_CARD',
    'REDACTED_HEX',
    'REDACTED_VALUE',
]

__version__ = '1.0.0'
