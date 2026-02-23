#!/usr/bin/env python3
"""
Telemetry Tracker - Central Event Dispatcher

Routes telemetry events to appropriate destinations (Umami, New Relic)
based on configuration and event category.

Usage:
    from shared.telemetry import track, telemetry
    
    # Simple tracking
    track('generation.started', model='flux-schnell', credits_cost=10)
    
    # With user context
    track('checkout.completed', user_id='user123', amount=29.99)
    
    # Access tracker directly
    telemetry.set_context(user_id='user123', session_id='sess456')
    telemetry.track('page.view', path='/generate')
"""

import os
import threading
from typing import Any, Dict, Optional, Callable
from contextlib import contextmanager

from .event import (
    TelemetryEvent,
    EventCategory,
    EventDestination,
)


class Telemetry:
    """
    Central telemetry dispatcher.
    
    Routes events to Umami (user behavior analytics) and/or
    New Relic (operational logs) based on event category.
    """
    
    _instance: Optional["Telemetry"] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Initialize telemetry tracker."""
        self._enabled = True
        self._debug = os.getenv("TELEMETRY_DEBUG", "false").lower() == "true"
        
        # Request context (thread-local)
        self._context = threading.local()
        
        # Lazy-loaded clients
        self._umami = None
        self._logger = None
        
        # Custom handlers
        self._handlers: Dict[str, Callable] = {}
        
    @classmethod
    def get_instance(cls) -> "Telemetry":
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @property
    def umami(self):
        """Lazy-load Umami client."""
        if self._umami is None:
            try:
                from shared.analytics import UmamiAnalytics, get_analytics
                self._umami = get_analytics()
                # Force sync mode for immediate delivery
                # The async queue may not flush before process exits
                if self._umami:
                    self._umami._async_enabled = False
            except ImportError:
                if self._debug:
                    print("[TELEMETRY] Umami analytics not available")
                self._umami = None
        return self._umami
    
    @property
    def logger(self):
        """Lazy-load AppLogger."""
        if self._logger is None:
            try:
                from shared.logging import get_logger
                self._logger = get_logger("telemetry")
            except ImportError:
                if self._debug:
                    print("[TELEMETRY] Logger not available")
                self._logger = None
        return self._logger
    
    def enable(self):
        """Enable telemetry tracking."""
        self._enabled = True
    
    def disable(self):
        """Disable telemetry tracking."""
        self._enabled = False
    
    def set_debug(self, debug: bool):
        """Set debug mode."""
        self._debug = debug
    
    def set_context(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        hostname: Optional[str] = None,
        path: Optional[str] = None,
        referrer: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """
        Set request context for the current thread.
        
        This context will be automatically added to all events
        tracked from this thread.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            request_id: Request identifier
            hostname: Request hostname
            path: Request path
            referrer: Request referrer
            user_agent: User agent string
            ip_address: Client IP (will be hashed)
        """
        self._context.user_id = user_id
        self._context.session_id = session_id
        self._context.request_id = request_id
        self._context.hostname = hostname
        self._context.path = path
        self._context.referrer = referrer
        self._context.user_agent = user_agent
        self._context.ip_address = ip_address
    
    def clear_context(self):
        """Clear request context for the current thread."""
        for attr in ['user_id', 'session_id', 'request_id', 'hostname', 
                     'path', 'referrer', 'user_agent', 'ip_address']:
            if hasattr(self._context, attr):
                delattr(self._context, attr)
    
    @contextmanager
    def context(self, **kwargs):
        """
        Context manager for temporary context.
        
        Usage:
            with telemetry.context(user_id='user123'):
                track('page.view', path='/home')
        """
        # Save existing context
        saved = {}
        for key in kwargs:
            if hasattr(self._context, key):
                saved[key] = getattr(self._context, key)
        
        # Set new context
        self.set_context(**kwargs)
        
        try:
            yield
        finally:
            # Restore saved context
            self.clear_context()
            for key, value in saved.items():
                setattr(self._context, key, value)
    
    def get_context(self) -> Dict[str, Any]:
        """Get current thread context."""
        return {
            'user_id': getattr(self._context, 'user_id', None),
            'session_id': getattr(self._context, 'session_id', None),
            'request_id': getattr(self._context, 'request_id', None),
            'hostname': getattr(self._context, 'hostname', None),
            'path': getattr(self._context, 'path', None),
            'referrer': getattr(self._context, 'referrer', None),
            'user_agent': getattr(self._context, 'user_agent', None),
            'ip_address': getattr(self._context, 'ip_address', None),
        }
    
    def add_handler(self, name: str, handler: Callable):
        """
        Add custom event handler.
        
        Args:
            name: Handler name
            handler: Callable that receives TelemetryEvent
        """
        self._handlers[name] = handler
    
    def remove_handler(self, name: str):
        """Remove custom event handler."""
        self._handlers.pop(name, None)
    
    def _infer_category(self, event_name: str) -> EventCategory:
        """Infer event category from event name."""
        prefix = event_name.split('.')[0].lower()
        
        category_map = {
            'auth': EventCategory.AUTH,
            'login': EventCategory.AUTH,
            'signup': EventCategory.AUTH,
            'logout': EventCategory.AUTH,
            'generation': EventCategory.GENERATION,
            'generate': EventCategory.GENERATION,
            'image': EventCategory.GENERATION,
            'checkout': EventCategory.CHECKOUT,
            'payment': EventCategory.CHECKOUT,
            'purchase': EventCategory.CHECKOUT,
            'stripe': EventCategory.CHECKOUT,
            'credits': EventCategory.CREDITS,
            'credit': EventCategory.CREDITS,
            'ui': EventCategory.UI,
            'page': EventCategory.UI,
            'click': EventCategory.UI,
            'modal': EventCategory.UI,
            'button': EventCategory.UI,
            'api': EventCategory.API,
            'request': EventCategory.API,
            'response': EventCategory.API,
            'error': EventCategory.ERROR,
            'exception': EventCategory.ERROR,
            'session': EventCategory.SESSION,
            'performance': EventCategory.PERFORMANCE,
            'timing': EventCategory.PERFORMANCE,
            'duration': EventCategory.PERFORMANCE,
        }
        
        return category_map.get(prefix, EventCategory.SYSTEM)
    
    def track(
        self,
        event_name: str,
        category: Optional[EventCategory] = None,
        **data
    ) -> Optional[TelemetryEvent]:
        """
        Track an event.
        
        Args:
            event_name: Event name (e.g., 'generation.started')
            category: Optional category override
            **data: Event data
            
        Returns:
            The tracked TelemetryEvent or None if disabled/not sampled.
        """
        if not self._enabled:
            return None
        
        # Extract special fields from data
        user_id = data.pop('user_id', None)
        session_id = data.pop('session_id', None)
        request_id = data.pop('request_id', None)
        
        # Infer category if not provided
        if category is None:
            category = self._infer_category(event_name)
        
        # Create event
        event = TelemetryEvent(
            name=event_name,
            category=category,
            user_id=user_id or getattr(self._context, 'user_id', None),
            session_id=session_id or getattr(self._context, 'session_id', None),
            request_id=request_id or getattr(self._context, 'request_id', None),
            hostname=getattr(self._context, 'hostname', None),
            path=getattr(self._context, 'path', None),
            referrer=getattr(self._context, 'referrer', None),
            user_agent=getattr(self._context, 'user_agent', None),
            ip_address=getattr(self._context, 'ip_address', None),
            data=data
        )
        
        # Check sampling
        if not event.should_sample():
            if self._debug:
                print(f"[TELEMETRY] Event dropped by sampling: {event_name}")
            return None
        
        # Debug logging
        if self._debug:
            print(f"[TELEMETRY] Tracking: {event_name} -> {event.destination.value}")
        
        # Route to destinations
        self._route_event(event)
        
        # Call custom handlers
        for handler in self._handlers.values():
            try:
                handler(event)
            except Exception as e:
                if self._debug:
                    print(f"[TELEMETRY] Handler error: {e}")
        
        return event
    
    def _route_event(self, event: TelemetryEvent):
        """Route event to appropriate destinations."""
        destination = event.destination
        
        # Route to Umami
        if destination in (EventDestination.UMAMI, EventDestination.BOTH):
            self._send_to_umami(event)
        
        # Route to New Relic
        if destination in (EventDestination.NEWRELIC, EventDestination.BOTH):
            self._send_to_newrelic(event)
    
    def _send_to_umami(self, event: TelemetryEvent):
        """Send event to Umami analytics."""
        if self.umami is None:
            return
        
        try:
            umami_data = event.to_umami_event()
            
            # Add hostname and referrer to event_data if present
            data = umami_data.get('data', {})
            if event.hostname:
                data['hostname'] = event.hostname
            if event.referrer:
                data['referrer'] = event.referrer
            
            self.umami.track_event(
                event_name=umami_data['name'],
                event_data=data,
                url=event.path or '/'
            )
        except Exception as e:
            if self._debug:
                print(f"[TELEMETRY] Umami error: {e}")
    
    def _send_to_newrelic(self, event: TelemetryEvent):
        """Send event to New Relic."""
        if self.logger is None:
            return
        
        try:
            log_data = event.to_newrelic_log()
            
            # Use appropriate log level based on category
            if event.category == EventCategory.ERROR:
                self.logger.error(log_data['message'], extra=log_data)
            elif event.category == EventCategory.PERFORMANCE:
                self.logger.debug(log_data['message'], extra=log_data)
            else:
                self.logger.info(log_data['message'], extra=log_data)
                
        except Exception as e:
            if self._debug:
                print(f"[TELEMETRY] New Relic error: {e}")
    
    def track_event(self, event: TelemetryEvent) -> Optional[TelemetryEvent]:
        """
        Track a pre-constructed event.
        
        Args:
            event: TelemetryEvent instance
            
        Returns:
            The tracked event or None if disabled/not sampled.
        """
        if not self._enabled:
            return None
        
        if not event.should_sample():
            return None
        
        self._route_event(event)
        
        for handler in self._handlers.values():
            try:
                handler(event)
            except Exception as e:
                if self._debug:
                    print(f"[TELEMETRY] Handler error: {e}")
        
        return event
    
    # Convenience methods for common events
    
    def page_view(self, path: str, **data):
        """Track a page view."""
        return self.track('page.view', category=EventCategory.UI, path=path, **data)
    
    def button_click(self, button_id: str, **data):
        """Track a button click."""
        return self.track('button.click', category=EventCategory.UI, button_id=button_id, **data)
    
    def error(self, error_type: str, message: str, **data):
        """Track an error."""
        return self.track('error', category=EventCategory.ERROR, error_type=error_type, error_message=message, **data)
    
    def generation_started(self, model: str, **data):
        """Track generation start."""
        return self.track('generation.started', category=EventCategory.GENERATION, model=model, **data)
    
    def generation_completed(self, model: str, duration_ms: int, **data):
        """Track generation completion."""
        return self.track('generation.completed', category=EventCategory.GENERATION, model=model, duration_ms=duration_ms, **data)
    
    def generation_failed(self, model: str, error: str, **data):
        """Track generation failure."""
        return self.track('generation.failed', category=EventCategory.GENERATION, model=model, error=error, **data)
    
    def credits_deducted(self, amount: int, reason: str, **data):
        """Track credits deduction."""
        return self.track('credits.deducted', category=EventCategory.CREDITS, amount=amount, reason=reason, **data)
    
    def checkout_started(self, package: str, amount: float, **data):
        """Track checkout start."""
        return self.track('checkout.started', category=EventCategory.CHECKOUT, package=package, amount=amount, **data)
    
    def checkout_completed(self, package: str, amount: float, **data):
        """Track checkout completion."""
        return self.track('checkout.completed', category=EventCategory.CHECKOUT, package=package, amount=amount, **data)


# Singleton accessor
def get_telemetry() -> Telemetry:
    """Get the telemetry singleton."""
    return Telemetry.get_instance()


# Convenience function
def track(event_name: str, **data) -> Optional[TelemetryEvent]:
    """
    Track an event.
    
    This is a convenience function that uses the singleton telemetry instance.
    
    Args:
        event_name: Event name (e.g., 'generation.started')
        **data: Event data
        
    Returns:
        The tracked TelemetryEvent or None.
        
    Usage:
        track('generation.started', model='flux-schnell', user_id='user123')
        track('checkout.completed', amount=29.99, package='starter')
    """
    return get_telemetry().track(event_name, **data)


def track_event(event: TelemetryEvent) -> Optional[TelemetryEvent]:
    """
    Track a pre-constructed event.
    
    Args:
        event: TelemetryEvent instance
        
    Returns:
        The tracked event or None.
    """
    return get_telemetry().track_event(event)


# Create default instance alias
telemetry = get_telemetry()
