"""
Umami Analytics - Privacy-First, Universal Analytics for Python

A production-ready analytics module that integrates with Umami Analytics.
Designed with privacy, configurability, and reusability as core values.

PRIVACY GUARANTEE:
- This module ONLY sends text-based events and metrics
- NO screenshots, session recordings, or DOM captures
- ALL URLs and data are sanitized before transmission
- PII (emails, tokens, etc.) is automatically redacted

Features:
- Async event queue (non-blocking)
- Flask middleware integration
- Automatic PII sanitization
- Request context forwarding
- Configurable via YAML + environment variables
- Graceful degradation (no crashes if disabled)

Quick Start:
    from shared.analytics import get_analytics
    
    # Get analytics instance
    analytics = get_analytics(app_name='my_app')
    
    # Track events
    analytics.track_event('signup', {'plan': 'pro'})
    analytics.track_page_view('/dashboard')
    
    # Flask integration
    analytics.init_flask(app)  # Auto-tracks all requests

Environment Variables:
    UMAMI_WEBSITE_ID  - Your Umami website ID (required)
    UMAMI_API_URL     - API endpoint (default: https://cloud.umami.is)
    UMAMI_API_KEY     - API key for authenticated requests
    UMAMI_ENABLED     - Enable/disable (true/false)
    UMAMI_DEBUG       - Debug mode (true/false)
"""

import os
import json
import time
import queue
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone
from functools import wraps

import yaml

# Import our sanitizer
from .sanitizer import sanitize_url, sanitize_data, is_pii_detected

# Try to import our logging module
try:
    from shared.logging import get_logger, LogCategory, set_log_category
    HAS_SHARED_LOGGING = True
except ImportError:
    HAS_SHARED_LOGGING = False
    import logging
    def get_logger(name, **kwargs):
        return logging.getLogger(name)
    class LogCategory:
        API = 'api'


# =============================================================================
# CONFIGURATION LOADING
# =============================================================================

def _load_yaml_config(config_path: Path) -> Dict:
    """Load YAML configuration file."""
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def _get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean from environment variable."""
    val = os.environ.get(key, '').lower()
    if val in ('true', '1', 'yes', 'on'):
        return True
    if val in ('false', '0', 'no', 'off'):
        return False
    return default


def _merge_config(*configs: Dict) -> Dict:
    """Deep merge multiple configuration dictionaries."""
    result = {}
    for config in configs:
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = _merge_config(result[key], value)
            else:
                result[key] = value
    return result


# =============================================================================
# UMAMI ANALYTICS CLASS
# =============================================================================

class UmamiAnalytics:
    """
    Universal, Privacy-First Umami Analytics Client.
    
    This class provides:
    - Async event sending (non-blocking)
    - Automatic PII sanitization
    - Flask middleware integration
    - Request context forwarding
    - Graceful degradation
    
    PRIVACY NOTICE:
    This implementation ONLY sends text-based events and metrics.
    No screenshots, session recordings, or DOM captures are performed.
    All URLs and data are sanitized before transmission.
    """
    
    _instances: Dict[str, 'UmamiAnalytics'] = {}
    _global_config: Optional[Dict] = None
    
    def __init__(self, app_name: str = 'default', config: Optional[Dict] = None):
        """
        Initialize Umami Analytics.
        
        Args:
            app_name: Application name for identification
            config: Optional configuration override
        """
        self.app_name = app_name
        self._config = self._load_config(config)
        self._logger = get_logger(__name__, app_name=app_name)
        
        # Core settings
        self.api_url = os.environ.get('UMAMI_API_URL', 
                                       self._config.get('umami', {}).get('api_url', 'https://cloud.umami.is'))
        self.website_id = os.environ.get('UMAMI_WEBSITE_ID',
                                          self._config.get('umami', {}).get('website_id'))
        self.api_key = os.environ.get('UMAMI_API_KEY',
                                       self._config.get('umami', {}).get('api_key'))
        # Hostname: env var > config > app_name (ensure not None)
        config_hostname = self._config.get('umami', {}).get('hostname')
        self.hostname = os.environ.get('UMAMI_HOSTNAME') or config_hostname or app_name or 'localhost'
        
        # Determine if enabled
        env_enabled = os.environ.get('UMAMI_ENABLED')
        if env_enabled is not None:
            self.enabled = _get_env_bool('UMAMI_ENABLED', True)
        else:
            env = os.environ.get('FLASK_ENV', os.environ.get('ENVIRONMENT', 'development'))
            env_config = self._config.get('environments', {}).get(env, {})
            self.enabled = env_config.get('umami', {}).get('enabled', 
                                          self._config.get('umami', {}).get('enabled', True))
        
        # Debug mode
        self.debug = _get_env_bool('UMAMI_DEBUG', False)
        
        # Validate required config
        if self.enabled and not self.website_id:
            self._logger.warning("Umami Analytics disabled: UMAMI_WEBSITE_ID not configured")
            self.enabled = False
        
        # Timeout and retry settings
        self.timeout = self._config.get('umami', {}).get('timeout', 5)
        self.retry_attempts = self._config.get('umami', {}).get('retry_attempts', 2)
        self.retry_delay = self._config.get('umami', {}).get('retry_delay', 0.5)
        
        # Privacy config
        self._privacy_config = self._config.get('privacy', {})
        
        # Flask config
        self._flask_config = self._config.get('flask', {})
        
        # Async queue
        async_config = self._config.get('async', {})
        self._async_enabled = async_config.get('enabled', True)
        self._batch_size = async_config.get('batch_size', 10)
        self._flush_interval = async_config.get('flush_interval', 5.0)
        self._max_queue_size = async_config.get('max_queue_size', 1000)
        
        # Initialize async components
        self._queue: queue.Queue = queue.Queue(maxsize=self._max_queue_size)
        self._shutdown = threading.Event()
        self._sender_thread: Optional[threading.Thread] = None
        
        if self.enabled and self._async_enabled:
            self._start_sender_thread()
        
        if self.enabled:
            self._debug_log(f"Umami Analytics initialized for {app_name}")
            self._debug_log(f"  API URL: {self.api_url}")
            self._debug_log(f"  Website ID: {self.website_id[:8]}...")
    
    def _load_config(self, override_config: Optional[Dict] = None) -> Dict:
        """Load and merge configuration from all sources."""
        # Load global config (cached)
        if UmamiAnalytics._global_config is None:
            global_path = Path(__file__).parent / 'config.yaml'
            UmamiAnalytics._global_config = _load_yaml_config(global_path)
        
        # Start with global config
        config = dict(UmamiAnalytics._global_config)
        
        # Apply environment-specific overrides
        env = os.environ.get('FLASK_ENV', os.environ.get('ENVIRONMENT', 'development'))
        if env in config.get('environments', {}):
            config = _merge_config(config, config['environments'][env])
        
        # Apply override config
        if override_config:
            config = _merge_config(config, override_config)
        
        return config
    
    def _debug_log(self, message: str, is_error: bool = False):
        """Log debug message if debug mode is enabled."""
        if self.debug:
            if is_error:
                print(f"[UMAMI ERROR] {message}")
            else:
                print(f"[UMAMI] {message}")
    
    def _start_sender_thread(self):
        """Start background thread for async event sending."""
        self._sender_thread = threading.Thread(
            target=self._send_loop,
            daemon=True,
            name=f"umami-sender-{self.app_name}"
        )
        self._sender_thread.start()
    
    def _send_loop(self):
        """Background thread that batches and sends events."""
        while not self._shutdown.is_set():
            events = []
            
            try:
                # Wait for first event or timeout
                events.append(self._queue.get(timeout=self._flush_interval))
                
                # Collect more events if available
                while len(events) < self._batch_size:
                    try:
                        events.append(self._queue.get_nowait())
                    except queue.Empty:
                        break
            except queue.Empty:
                continue
            
            # Send batch
            if events:
                for event in events:
                    self._send_event_sync(event)
    
    def _send_event_sync(self, event: Dict) -> bool:
        """
        Send a single event to Umami (synchronous).
        
        Args:
            event: Event payload to send
            
        Returns:
            True if successful, False otherwise
        """
        import urllib.request
        import urllib.error
        
        endpoint = f"{self.api_url.rstrip('/')}/api/send"
        
        # Build payload (Umami V2 format)
        payload = json.dumps(event).encode('utf-8')
        
        # Headers - MUST use a proper browser User-Agent or Umami rejects the request
        # See: https://umami.is/docs/api/sending-stats
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Add API key if available
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        # Add forwarded IP if available
        if 'client_ip' in event:
            headers['X-Forwarded-For'] = event.pop('client_ip')
        
        for attempt in range(self.retry_attempts):
            try:
                request = urllib.request.Request(
                    endpoint,
                    data=payload,
                    headers=headers,
                    method='POST'
                )
                
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    if response.status in (200, 202):
                        self._debug_log(f"Event sent: {event.get('payload', {}).get('name', 'pageview')}")
                        return True
                    else:
                        self._debug_log(f"Unexpected response: {response.status}", is_error=True)
                        
            except urllib.error.HTTPError as e:
                self._debug_log(f"HTTP Error {e.code}: {e.reason}", is_error=True)
                if e.code < 500:  # Don't retry client errors
                    break
            except urllib.error.URLError as e:
                self._debug_log(f"URL Error: {e}", is_error=True)
            except Exception as e:
                self._debug_log(f"Send Error: {e}", is_error=True)
            
            if attempt < self.retry_attempts - 1:
                time.sleep(self.retry_delay)
        
        return False
    
    def _build_event_payload(self, 
                              event_type: str,
                              url: str,
                              event_name: Optional[str] = None,
                              event_data: Optional[Dict] = None,
                              user_agent: Optional[str] = None,
                              client_ip: Optional[str] = None,
                              referrer: Optional[str] = None) -> Dict:
        """Build Umami event payload."""
        # Sanitize URL
        clean_url = sanitize_url(url, self._privacy_config)
        
        # Sanitize event data
        clean_data = sanitize_data(event_data, self._privacy_config) if event_data else None
        
        # Build payload
        payload = {
            'type': 'event',
            'payload': {
                'website': self.website_id,
                'hostname': self.hostname,
                'url': clean_url,
                'screen': '1920x1080',  # Default for backend events
                'language': 'en-US',
            }
        }
        
        # Add event name (for custom events)
        if event_name:
            payload['payload']['name'] = event_name
        
        # Add event data
        if clean_data:
            payload['payload']['data'] = clean_data
        
        # Add user agent
        if user_agent:
            payload['payload']['user_agent'] = user_agent
        
        # Add referrer (sanitized)
        if referrer:
            payload['payload']['referrer'] = sanitize_url(referrer, self._privacy_config)
        
        # Store client IP for header (not in payload)
        if client_ip:
            payload['client_ip'] = client_ip
        
        return payload
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def track_event(self,
                    event_name: str,
                    event_data: Optional[Dict] = None,
                    url: str = '/',
                    user_agent: Optional[str] = None,
                    client_ip: Optional[str] = None) -> bool:
        """
        Track a custom event.
        
        Args:
            event_name: Name of the event (e.g., 'signup', 'purchase')
            event_data: Additional event metadata
            url: URL/path where event occurred
            user_agent: Client's user agent (for attribution)
            client_ip: Client's IP (for geolocation)
            
        Returns:
            True if event was queued/sent successfully
            
        Example:
            analytics.track_event('purchase', {'plan': 'pro', 'amount': 29.99})
        """
        if not self.enabled:
            return False
        
        payload = self._build_event_payload(
            event_type='event',
            url=url,
            event_name=event_name,
            event_data=event_data,
            user_agent=user_agent,
            client_ip=client_ip
        )
        
        # Log the event
        if HAS_SHARED_LOGGING:
            set_log_category(LogCategory.API)
        self._logger.debug("Tracking event", 
                          event=event_name, 
                          url=sanitize_url(url, self._privacy_config))
        
        # Queue or send
        if self._async_enabled:
            try:
                self._queue.put_nowait(payload)
                return True
            except queue.Full:
                self._debug_log("Event queue full, dropping event", is_error=True)
                return False
        else:
            return self._send_event_sync(payload)
    
    def track_page_view(self,
                        url: str,
                        referrer: Optional[str] = None,
                        user_agent: Optional[str] = None,
                        client_ip: Optional[str] = None) -> bool:
        """
        Track a page view.
        
        Args:
            url: URL/path of the page
            referrer: Referring URL
            user_agent: Client's user agent
            client_ip: Client's IP
            
        Returns:
            True if event was queued/sent successfully
        """
        if not self.enabled:
            return False
        
        payload = self._build_event_payload(
            event_type='pageview',
            url=url,
            referrer=referrer,
            user_agent=user_agent,
            client_ip=client_ip
        )
        
        self._logger.debug("Tracking page view", url=sanitize_url(url, self._privacy_config))
        
        if self._async_enabled:
            try:
                self._queue.put_nowait(payload)
                return True
            except queue.Full:
                return False
        else:
            return self._send_event_sync(payload)
    
    def track_error(self,
                    error: Exception,
                    url: str = '/',
                    additional_data: Optional[Dict] = None) -> bool:
        """
        Track an error event.
        
        Args:
            error: The exception that occurred
            url: URL where error occurred
            additional_data: Extra context
            
        Returns:
            True if event was queued/sent successfully
        """
        if not self.enabled:
            return False
        
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error)[:200],  # Truncate long messages
        }
        
        if additional_data:
            error_data.update(additional_data)
        
        return self.track_event('error', error_data, url=url)
    
    # =========================================================================
    # FLASK INTEGRATION
    # =========================================================================
    
    def init_flask(self, app) -> None:
        """
        Initialize Flask integration with automatic request tracking.
        
        Args:
            app: Flask application instance
            
        Usage:
            from flask import Flask
            from shared.analytics import get_analytics
            
            app = Flask(__name__)
            analytics = get_analytics('my_app')
            analytics.init_flask(app)
        """
        if not self.enabled:
            self._logger.info("Umami Analytics disabled, skipping Flask integration")
            return
        
        exclude_paths = set(self._flask_config.get('exclude_paths', []))
        track_timing = self._flask_config.get('track_timing', True)
        track_errors = self._flask_config.get('track_errors', True)
        auto_track = self._flask_config.get('auto_track_requests', True)
        
        if not auto_track:
            return
        
        @app.before_request
        def _umami_before_request():
            from flask import request, g
            
            # Skip excluded paths
            if any(request.path.startswith(p) for p in exclude_paths):
                g._umami_skip = True
                return
            
            g._umami_skip = False
            g._umami_start_time = time.time()
        
        @app.after_request
        def _umami_after_request(response):
            from flask import request, g
            
            if getattr(g, '_umami_skip', True):
                return response
            
            # Calculate duration
            duration_ms = None
            if track_timing and hasattr(g, '_umami_start_time'):
                duration_ms = int((time.time() - g._umami_start_time) * 1000)
            
            # Build event data
            event_data = {
                'method': request.method,
                'status_code': response.status_code,
            }
            
            if duration_ms is not None:
                event_data['duration_ms'] = duration_ms
            
            # Determine event type
            if response.status_code >= 400 and track_errors:
                event_name = 'error_response'
                event_data['error_code'] = response.status_code
            else:
                event_name = 'api_request'
            
            # Track the request
            self.track_event(
                event_name=event_name,
                event_data=event_data,
                url=request.path,
                user_agent=request.headers.get('User-Agent'),
                client_ip=request.headers.get('X-Forwarded-For', request.remote_addr)
            )
            
            return response
        
        self._logger.info("Flask integration initialized",
                         auto_track=auto_track,
                         track_timing=track_timing,
                         excluded_paths=list(exclude_paths))
    
    # =========================================================================
    # LIFECYCLE
    # =========================================================================
    
    def flush(self) -> None:
        """Flush all pending events (blocking)."""
        if not self._async_enabled:
            return
        
        remaining = []
        while not self._queue.empty():
            try:
                remaining.append(self._queue.get_nowait())
            except queue.Empty:
                break
        
        for event in remaining:
            self._send_event_sync(event)
    
    def shutdown(self) -> None:
        """Shutdown analytics, flushing remaining events."""
        self._shutdown.set()
        self.flush()
        
        if self._sender_thread and self._sender_thread.is_alive():
            self._sender_thread.join(timeout=2)
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.shutdown()
        except:
            pass


# =============================================================================
# DECORATOR
# =============================================================================

def track_route(analytics: UmamiAnalytics, event_name: Optional[str] = None):
    """
    Decorator to track Flask route calls.
    
    Args:
        analytics: UmamiAnalytics instance
        event_name: Custom event name (defaults to function name)
        
    Usage:
        @app.route('/api/generate')
        @track_route(analytics, 'image_generation')
        def generate():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            start = time.time()
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration_ms = int((time.time() - start) * 1000)
                
                event_data = {
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                    'success': error is None,
                }
                
                if error:
                    event_data['error_type'] = type(error).__name__
                
                analytics.track_event(
                    event_name=event_name or func.__name__,
                    event_data=event_data,
                    url=request.path if 'request' in dir() else '/',
                    user_agent=request.headers.get('User-Agent') if 'request' in dir() else None
                )
        
        return wrapper
    return decorator


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def get_analytics(app_name: str = 'default', config: Optional[Dict] = None) -> UmamiAnalytics:
    """
    Get or create a UmamiAnalytics instance for the given app.
    
    Args:
        app_name: Application identifier
        config: Optional configuration override
        
    Returns:
        UmamiAnalytics instance (cached per app_name)
        
    Usage:
        from shared.analytics import get_analytics
        
        analytics = get_analytics('my_app')
        analytics.track_event('startup')
    """
    if app_name not in UmamiAnalytics._instances:
        UmamiAnalytics._instances[app_name] = UmamiAnalytics(app_name, config)
    return UmamiAnalytics._instances[app_name]


# Convenience function
def track_event(event_name: str, event_data: Optional[Dict] = None, **kwargs) -> bool:
    """
    Quick track event using default analytics instance.
    
    Args:
        event_name: Event name
        event_data: Event metadata
        **kwargs: Additional arguments for track_event
        
    Returns:
        True if successful
    """
    return get_analytics().track_event(event_name, event_data, **kwargs)


def track_page_view(url: str, **kwargs) -> bool:
    """
    Quick track page view using default analytics instance.
    
    Args:
        url: Page URL
        **kwargs: Additional arguments for track_page_view
        
    Returns:
        True if successful
    """
    return get_analytics().track_page_view(url, **kwargs)
