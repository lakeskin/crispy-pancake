"""
Centralized logging system for all applications

Features:
- Structured JSON logging with automatic context injection
- Request context tracking (user_id, trace_id, request path)
- Automatic stack trace capture for errors
- New Relic integration with configurable verbosity
- Log categories for dashboard filtering
- Timing utilities for performance tracking
- Sensitive data filtering

Quick Start:
    from shared.logging import get_logger, set_request_context, LogCategory
    
    # Get a logger
    logger = get_logger(__name__, app_name='my_app')
    
    # Set request context (in before_request)
    set_request_context(user_id='123', request_path='/api/test')
    
    # Log with automatic context
    logger.info("Operation started", operation='test')
    logger.error("Operation failed", error=exception)
    
    # Time operations
    from shared.logging import Timer, log_duration
    
    with Timer() as t:
        do_something()
    logger.info(f"Took {t.duration_ms}ms")
"""

from .logger import (
    # Core logger
    AppLogger, 
    get_logger,
    
    # Context management
    set_request_context,
    clear_request_context,
    get_request_context,
    set_user_context,
    set_log_category,
    
    # Log categories
    LogCategory,
    
    # Timing utilities
    Timer,
    log_duration,
    
    # Timezone-safe timestamp utilities (avoid the double-timezone bug)
    get_epoch_ms,
    get_epoch_seconds,
    get_utc_iso,
)

__all__ = [
    # Core
    'AppLogger', 
    'get_logger',
    
    # Context management
    'set_request_context',
    'clear_request_context',
    'get_request_context',
    'set_user_context',
    'set_log_category',
    
    # Categories
    'LogCategory',
    
    # Timing
    'Timer',
    'log_duration',
    
    # Timestamp utilities - use these instead of datetime.utcnow().timestamp()
    'get_epoch_ms',
    'get_epoch_seconds', 
    'get_utc_iso',
]
