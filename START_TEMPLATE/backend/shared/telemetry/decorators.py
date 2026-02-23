#!/usr/bin/env python3
"""
Telemetry Decorators

Provides decorators for automatic telemetry tracking on functions and methods.

Usage:
    from shared.telemetry import track_duration, track_function, track_error

    @track_duration('generation')
    def generate_image(prompt, model):
        ...

    @track_function
    def process_payment(amount):
        ...

    @track_error('payment')
    def risky_operation():
        ...
"""

import time
import functools
import traceback
from typing import Any, Callable, Optional, TypeVar, Union

from .event import EventCategory, TelemetryEvent
from .tracker import get_telemetry


F = TypeVar('F', bound=Callable[..., Any])


def track_duration(
    event_name: str,
    category: Optional[EventCategory] = None,
    include_args: bool = False,
    include_result: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to track function execution duration.
    
    Tracks two events:
    - {event_name}.started - when function starts
    - {event_name}.completed - when function completes (with duration_ms)
    - {event_name}.failed - if function raises exception
    
    Args:
        event_name: Base event name (e.g., 'generation')
        category: Optional category override
        include_args: Include function arguments in event data
        include_result: Include function return value in completed event
        
    Returns:
        Decorated function
        
    Usage:
        @track_duration('generation', category=EventCategory.GENERATION)
        def generate_image(prompt, model='flux-schnell'):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            
            # Prepare event data
            event_data = {}
            if include_args:
                # Include positional args (skip self for methods)
                arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
                for i, (name, value) in enumerate(zip(arg_names, args)):
                    if name != 'self':
                        event_data[f'arg_{name}'] = _safe_repr(value)
                # Include keyword args
                for key, value in kwargs.items():
                    event_data[f'arg_{key}'] = _safe_repr(value)
            
            # Track start
            start_time = time.time()
            telemetry.track(f'{event_name}.started', category=category, **event_data)
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Track completion
                duration_ms = int((time.time() - start_time) * 1000)
                completion_data = {
                    'duration_ms': duration_ms,
                    'success': True,
                    **event_data
                }
                
                if include_result:
                    completion_data['result'] = _safe_repr(result)
                
                telemetry.track(f'{event_name}.completed', category=category, **completion_data)
                
                return result
                
            except Exception as e:
                # Track failure
                duration_ms = int((time.time() - start_time) * 1000)
                telemetry.track(
                    f'{event_name}.failed',
                    category=EventCategory.ERROR if category is None else category,
                    duration_ms=duration_ms,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    success=False,
                    **event_data
                )
                raise
        
        return wrapper  # type: ignore
    return decorator


def track_function(
    func: Optional[F] = None,
    *,
    category: Optional[EventCategory] = None,
    include_args: bool = False,
) -> Union[F, Callable[[F], F]]:
    """
    Decorator to track function calls.
    
    Simpler than track_duration - only tracks a single event with duration.
    
    Can be used with or without parentheses:
        @track_function
        def my_func(): ...
        
        @track_function(category=EventCategory.API)
        def my_api_func(): ...
    
    Args:
        func: Function to decorate (when used without parentheses)
        category: Optional category override
        include_args: Include function arguments in event data
        
    Returns:
        Decorated function
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            
            # Prepare event data
            event_data = {
                'function': fn.__name__,
                'module': fn.__module__,
            }
            
            if include_args:
                arg_names = fn.__code__.co_varnames[:fn.__code__.co_argcount]
                for i, (name, value) in enumerate(zip(arg_names, args)):
                    if name != 'self':
                        event_data[f'arg_{name}'] = _safe_repr(value)
                for key, value in kwargs.items():
                    event_data[f'arg_{key}'] = _safe_repr(value)
            
            start_time = time.time()
            
            try:
                result = fn(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                telemetry.track(
                    f'function.{fn.__name__}',
                    category=category,
                    duration_ms=duration_ms,
                    success=True,
                    **event_data
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                telemetry.track(
                    f'function.{fn.__name__}.error',
                    category=EventCategory.ERROR,
                    duration_ms=duration_ms,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    success=False,
                    **event_data
                )
                raise
        
        return wrapper  # type: ignore
    
    # Handle both @track_function and @track_function()
    if func is not None:
        return decorator(func)
    return decorator


def track_error(
    event_name: str = 'error',
    category: EventCategory = EventCategory.ERROR,
    reraise: bool = True,
) -> Callable[[F], F]:
    """
    Decorator to track errors from a function.
    
    Only tracks an event if the function raises an exception.
    
    Args:
        event_name: Event name for the error
        category: Event category (defaults to ERROR)
        reraise: Whether to re-raise the exception after tracking
        
    Returns:
        Decorated function
        
    Usage:
        @track_error('payment.error')
        def process_payment(amount):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                telemetry = get_telemetry()
                
                telemetry.track(
                    event_name,
                    category=category,
                    function=func.__name__,
                    module=func.__module__,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                )
                
                if reraise:
                    raise
                return None
        
        return wrapper  # type: ignore
    return decorator


def track_api_endpoint(
    endpoint_name: Optional[str] = None,
    track_request: bool = True,
    track_response: bool = True,
) -> Callable[[F], F]:
    """
    Decorator specifically for Flask/API endpoints.
    
    Tracks:
    - api.request - when endpoint is called
    - api.response - when endpoint returns (with status code and duration)
    
    Args:
        endpoint_name: Override endpoint name (defaults to function name)
        track_request: Whether to track request events
        track_response: Whether to track response events
        
    Returns:
        Decorated function
        
    Usage:
        @app.route('/api/generate', methods=['POST'])
        @track_api_endpoint()
        def generate():
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            name = endpoint_name or func.__name__
            
            # Try to get Flask request context
            request_data = {}
            try:
                from flask import request
                request_data = {
                    'method': request.method,
                    'path': request.path,
                    'endpoint': name,
                    'content_type': request.content_type,
                }
                # Set telemetry context
                telemetry.set_context(
                    path=request.path,
                    hostname=request.host,
                    user_agent=request.headers.get('User-Agent'),
                    referrer=request.headers.get('Referer'),
                )
            except (ImportError, RuntimeError):
                request_data = {'endpoint': name}
            
            # Track request
            if track_request:
                telemetry.track('api.request', category=EventCategory.API, **request_data)
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Determine status code
                status_code = 200
                if isinstance(result, tuple) and len(result) >= 2:
                    status_code = result[1]
                elif hasattr(result, 'status_code'):
                    status_code = result.status_code
                
                # Track response
                if track_response:
                    telemetry.track(
                        'api.response',
                        category=EventCategory.API,
                        endpoint=name,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        success=status_code < 400,
                    )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Track error response
                telemetry.track(
                    'api.error',
                    category=EventCategory.ERROR,
                    endpoint=name,
                    duration_ms=duration_ms,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                )
                raise
            finally:
                # Clear context
                telemetry.clear_context()
        
        return wrapper  # type: ignore
    return decorator


def _safe_repr(value: Any, max_length: int = 100) -> str:
    """
    Safely convert a value to string for event data.
    
    Truncates long values and handles non-serializable types.
    """
    try:
        if value is None:
            return 'None'
        if isinstance(value, (str, int, float, bool)):
            s = str(value)
        elif isinstance(value, (list, tuple)):
            s = f'{type(value).__name__}[{len(value)} items]'
        elif isinstance(value, dict):
            s = f'dict[{len(value)} keys]'
        else:
            s = f'{type(value).__name__}'
        
        if len(s) > max_length:
            return s[:max_length - 3] + '...'
        return s
    except Exception:
        return '<unrepresentable>'


# Flask middleware helper
def create_flask_telemetry_middleware(app):
    """
    Create Flask middleware for automatic request telemetry.
    
    This sets up context for each request and tracks request/response.
    
    Usage:
        from flask import Flask
        from shared.telemetry.decorators import create_flask_telemetry_middleware
        
        app = Flask(__name__)
        create_flask_telemetry_middleware(app)
    
    Args:
        app: Flask application instance
    """
    from flask import request, g
    
    @app.before_request
    def before_request():
        g.request_start_time = time.time()
        
        telemetry = get_telemetry()
        telemetry.set_context(
            path=request.path,
            hostname=request.host,
            user_agent=request.headers.get('User-Agent'),
            referrer=request.headers.get('Referer'),
            request_id=request.headers.get('X-Request-ID'),
        )
    
    @app.after_request
    def after_request(response):
        telemetry = get_telemetry()
        
        duration_ms = 0
        if hasattr(g, 'request_start_time'):
            duration_ms = int((time.time() - g.request_start_time) * 1000)
        
        # Track API response (sampled)
        if request.path.startswith('/api/'):
            telemetry.track(
                'api.response',
                category=EventCategory.API,
                path=request.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        
        return response
    
    @app.teardown_request
    def teardown_request(exception):
        if exception:
            telemetry = get_telemetry()
            telemetry.track(
                'api.error',
                category=EventCategory.ERROR,
                path=request.path,
                method=request.method,
                error_type=type(exception).__name__,
                error_message=str(exception),
            )
        
        get_telemetry().clear_context()
