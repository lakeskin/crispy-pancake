#!/usr/bin/env python3
"""
Telemetry Event Schema

Provides a unified event schema for all telemetry events,
ensuring consistency across Umami analytics and New Relic logging.
"""

import time
import uuid
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class EventCategory(Enum):
    """Event categories for routing and filtering."""
    
    AUTH = "auth"
    GENERATION = "generation"
    CHECKOUT = "checkout"
    CREDITS = "credits"
    UI = "ui"
    API = "api"
    ERROR = "error"
    SESSION = "session"
    PERFORMANCE = "performance"
    SYSTEM = "system"


class EventDestination(Enum):
    """Destinations for event routing."""
    
    UMAMI = "umami"
    NEWRELIC = "newrelic"
    BOTH = "both"
    NONE = "none"


# Event to destination routing map
# Based on config.yaml routing rules
EVENT_ROUTING: Dict[EventCategory, EventDestination] = {
    EventCategory.AUTH: EventDestination.BOTH,
    EventCategory.GENERATION: EventDestination.BOTH,
    EventCategory.CHECKOUT: EventDestination.BOTH,
    EventCategory.CREDITS: EventDestination.BOTH,
    EventCategory.UI: EventDestination.UMAMI,
    EventCategory.SESSION: EventDestination.UMAMI,
    EventCategory.API: EventDestination.NEWRELIC,
    EventCategory.ERROR: EventDestination.NEWRELIC,
    EventCategory.PERFORMANCE: EventDestination.NEWRELIC,
    EventCategory.SYSTEM: EventDestination.NEWRELIC,
}


# Sampling rates by event type
SAMPLING_RATES: Dict[str, float] = {
    "api_request": 0.1,
    "api_response": 0.1,
    "page_view": 1.0,
    "generation.started": 1.0,
    "generation.completed": 1.0,
    "generation.failed": 1.0,
    "checkout.started": 1.0,
    "checkout.completed": 1.0,
    "auth.login": 1.0,
    "auth.signup": 1.0,
    "credits.deducted": 1.0,
    "error": 1.0,
}


@dataclass
class TelemetryEvent:
    """
    Unified telemetry event schema.
    
    This represents a single trackable event with all necessary context.
    Events are automatically enriched with timestamp, environment, and request context.
    """
    
    # Required fields
    name: str  # Event name like "generation.started" or "checkout.completed"
    category: EventCategory  # Category for routing
    
    # Auto-generated fields
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    
    # Context fields (optional)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Environment context (auto-populated)
    environment: str = field(default_factory=lambda: os.getenv("FLASK_ENV", os.getenv("NODE_ENV", "development")))
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "multi_image_generator"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    
    # Request context (optional, set by middleware)
    hostname: Optional[str] = None
    path: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Event-specific data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Computed destination (set after creation)
    destination: EventDestination = field(default=EventDestination.BOTH)
    
    def __post_init__(self):
        """Auto-set destination based on category routing rules."""
        self.destination = EVENT_ROUTING.get(self.category, EventDestination.BOTH)
    
    def should_sample(self) -> bool:
        """
        Determine if this event should be sampled based on rates.
        
        Returns:
            True if event should be tracked, False if it should be dropped.
        """
        import random
        
        # Get sampling rate for this event type
        rate = SAMPLING_RATES.get(self.name, 1.0)
        
        # If rate is 1.0, always sample
        if rate >= 1.0:
            return True
        
        # If rate is 0.0, never sample
        if rate <= 0.0:
            return False
        
        # Random sampling
        return random.random() < rate
    
    def to_umami_event(self) -> Dict[str, Any]:
        """
        Convert to Umami-compatible event format.
        
        Returns:
            Dictionary suitable for Umami API.
        """
        return {
            "name": self.name,
            "data": {
                "category": self.category.value,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "environment": self.environment,
                **self.data
            }
        }
    
    def to_newrelic_log(self) -> Dict[str, Any]:
        """
        Convert to New Relic log format.
        
        Returns:
            Dictionary suitable for New Relic Log API.
        """
        return {
            "message": f"[TELEMETRY] {self.name}",
            "event.name": self.name,
            "event.category": self.category.value,
            "event.id": self.event_id,
            "timestamp": self.timestamp_ms,
            "user.id": self.user_id,
            "session.id": self.session_id,
            "request.id": self.request_id,
            "environment": self.environment,
            "app.name": self.app_name,
            "app.version": self.app_version,
            "http.hostname": self.hostname,
            "http.path": self.path,
            "http.referer": self.referrer,
            "http.userAgent": self.user_agent,
            **{f"data.{k}": v for k, v in self.data.items()}
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to plain dictionary.
        
        Returns:
            Full event as dictionary.
        """
        result = asdict(self)
        result["category"] = self.category.value
        result["destination"] = self.destination.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelemetryEvent":
        """
        Create event from dictionary.
        
        Args:
            data: Dictionary with event data.
            
        Returns:
            TelemetryEvent instance.
        """
        # Convert category string to enum
        if isinstance(data.get("category"), str):
            data["category"] = EventCategory(data["category"])
        
        # Remove destination if present (will be computed)
        data.pop("destination", None)
        
        return cls(**data)
    
    def with_context(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        hostname: Optional[str] = None,
        path: Optional[str] = None,
        **extra_data
    ) -> "TelemetryEvent":
        """
        Return a new event with additional context.
        
        This is useful for enriching events with request context.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            request_id: Request identifier
            hostname: Request hostname
            path: Request path
            **extra_data: Additional data to merge
            
        Returns:
            New TelemetryEvent with merged context.
        """
        return TelemetryEvent(
            name=self.name,
            category=self.category,
            event_id=self.event_id,
            timestamp=self.timestamp,
            timestamp_ms=self.timestamp_ms,
            user_id=user_id or self.user_id,
            session_id=session_id or self.session_id,
            request_id=request_id or self.request_id,
            environment=self.environment,
            app_name=self.app_name,
            app_version=self.app_version,
            hostname=hostname or self.hostname,
            path=path or self.path,
            referrer=self.referrer,
            user_agent=self.user_agent,
            ip_address=self.ip_address,
            data={**self.data, **extra_data}
        )


# Convenience factory functions for common events
def auth_event(name: str, **data) -> TelemetryEvent:
    """Create an auth category event."""
    return TelemetryEvent(name=name, category=EventCategory.AUTH, data=data)


def generation_event(name: str, **data) -> TelemetryEvent:
    """Create a generation category event."""
    return TelemetryEvent(name=name, category=EventCategory.GENERATION, data=data)


def checkout_event(name: str, **data) -> TelemetryEvent:
    """Create a checkout category event."""
    return TelemetryEvent(name=name, category=EventCategory.CHECKOUT, data=data)


def credits_event(name: str, **data) -> TelemetryEvent:
    """Create a credits category event."""
    return TelemetryEvent(name=name, category=EventCategory.CREDITS, data=data)


def ui_event(name: str, **data) -> TelemetryEvent:
    """Create a UI category event."""
    return TelemetryEvent(name=name, category=EventCategory.UI, data=data)


def api_event(name: str, **data) -> TelemetryEvent:
    """Create an API category event."""
    return TelemetryEvent(name=name, category=EventCategory.API, data=data)


def error_event(name: str, **data) -> TelemetryEvent:
    """Create an error category event."""
    return TelemetryEvent(name=name, category=EventCategory.ERROR, data=data)


def performance_event(name: str, **data) -> TelemetryEvent:
    """Create a performance category event."""
    return TelemetryEvent(name=name, category=EventCategory.PERFORMANCE, data=data)
