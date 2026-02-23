"""
Telemetry Module - Unified Event Tracking

This module provides a centralized telemetry system that routes events
to multiple destinations (Umami, New Relic) based on configuration.

Usage:
    from shared.telemetry import track, track_event, telemetry

    # Simple tracking
    track('generation.started', model='flux-schnell', user_id=user.id)

    # With decorator
    @track_duration('generation')
    def generate_image(prompt):
        ...

    # Direct tracker access
    telemetry.track('checkout.completed', amount=29.99, user_id=user.id)
"""

from .tracker import Telemetry, get_telemetry, track, track_event
from .event import TelemetryEvent, EventCategory
from .decorators import track_duration, track_function, track_error

__all__ = [
    # Main tracker
    'Telemetry',
    'get_telemetry',
    'track',
    'track_event',
    
    # Event classes
    'TelemetryEvent',
    'EventCategory',
    
    # Decorators
    'track_duration',
    'track_function',
    'track_error',
]
