# 📡 Telemetry Module

Unified event tracking that routes to multiple destinations.

---

## 📦 Module Structure

```
shared/telemetry/
├── __init__.py      # Public exports
├── tracker.py       # Main Telemetry class
├── event.py         # Event types and categories
├── decorators.py    # Tracking decorators
└── config.yaml      # Telemetry configuration
```

---

## 🚀 Quick Start

```python
from shared.telemetry import track, track_duration

# Simple event tracking
track('generation.started', model='flux-schnell', user_id='123')

# Timing decorator
@track_duration('generation')
def generate_image(prompt):
    # Your code here
    return result
```

---

## 📖 API Reference

### `track(event_name: str, **properties)`

Track an event with properties.

```python
track('generation.started', 
    model='flux-dev', 
    user_id='user_123',
    credits_cost=10
)

track('checkout.completed',
    user_id='user_123',
    package_id='creator',
    amount=9.99
)
```

### `track_event(event_name: str, properties: dict)`

Alternative syntax with dict properties.

```python
track_event('button_click', {
    'button': 'submit',
    'page': '/signup'
})
```

### `@track_duration(event_prefix: str)`

Decorator that tracks function duration.

```python
@track_duration('api.generate')
def generate():
    # Automatically tracks:
    # - api.generate.started
    # - api.generate.completed (with duration_ms)
    # - api.generate.failed (if exception)
    pass
```

### `@track_function(event_name: str, **extra_props)`

More flexible function tracking.

```python
@track_function('generate_image', model='flux')
def generate(prompt):
    pass
```

### `@track_error(event_name: str)`

Track errors from a function.

```python
@track_error('critical_function')
def might_fail():
    # Errors automatically tracked with stack trace
    pass
```

---

## 🔄 Context Management

Set context that's automatically added to all events:

```python
from shared.telemetry import Telemetry

telemetry = Telemetry.get_instance()

# Set request context
telemetry.set_context(
    user_id='user_123',
    session_id='sess_456',
    request_id='req_789',
    hostname='myapp.com',
    path='/api/generate'
)

# All subsequent track() calls include this context
track('event.name', custom_prop='value')

# Clear context (e.g., after request)
telemetry.clear_context()
```

### Flask Middleware Pattern

```python
@app.before_request
def before_request():
    telemetry.set_context(
        user_id=get_current_user_id(),
        request_id=str(uuid.uuid4()),
        path=request.path
    )

@app.after_request
def after_request(response):
    telemetry.clear_context()
    return response
```

---

## 📊 Event Categories

```python
from shared.telemetry import EventCategory

class EventCategory:
    USER = 'user'           # User actions (clicks, navigation)
    GENERATION = 'generation'  # AI generations
    PAYMENT = 'payment'     # Payment events
    ERROR = 'error'         # Errors
    PERFORMANCE = 'performance'  # Timing/performance
    SYSTEM = 'system'       # System events
```

---

## 🎯 Common Tracking Patterns

### API Endpoint

```python
@app.route('/api/generate', methods=['POST'])
@require_auth
def generate():
    user = get_current_user()
    data = request.json
    
    # Track start
    track('generation.started',
        user_id=user['id'],
        model=data.get('model', 'default')
    )
    
    start = time.time()
    
    try:
        result = do_generation(data)
        
        # Track success
        track('generation.completed',
            user_id=user['id'],
            duration_ms=int((time.time() - start) * 1000),
            credits_used=10
        )
        
        return {'result': result}
        
    except Exception as e:
        # Track failure
        track('generation.failed',
            user_id=user['id'],
            error=str(e),
            duration_ms=int((time.time() - start) * 1000)
        )
        raise
```

### Using Decorators (Cleaner)

```python
@app.route('/api/generate', methods=['POST'])
@require_auth
@track_duration('api.generate')
def generate():
    user = get_current_user()
    
    # Context for detailed tracking
    track('generation.params',
        user_id=user['id'],
        model=request.json.get('model')
    )
    
    return do_generation(request.json)
```

---

## ⚙️ Configuration

### config.yaml

```yaml
telemetry:
  enabled: true
  debug: false
  
  destinations:
    umami:
      enabled: true
      events:
        - user.*
        - generation.*
        - payment.*
    
    logging:
      enabled: true
      level: INFO
      events:
        - error.*
        - system.*
  
  sampling:
    enabled: false
    rate: 1.0  # 100% of events
```

### Environment Variables

```bash
TELEMETRY_DEBUG=false
TELEMETRY_ENABLED=true
```

---

## 📚 Related Documentation

- [ANALYTICS.md](ANALYTICS.md) - Umami analytics
- [LOGGING.md](LOGGING.md) - Logging configuration
