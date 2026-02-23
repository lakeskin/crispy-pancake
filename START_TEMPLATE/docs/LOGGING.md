# 📝 Logging Module

Centralized, structured logging for all applications.

---

## 📦 Module Structure

```
shared/logging/
├── __init__.py      # Public exports
├── logger.py        # AppLogger class
└── config.yaml      # Logging configuration
```

---

## 🚀 Quick Start

```python
from shared.logging import get_logger, set_request_context

# Get a logger
logger = get_logger(__name__, app_name='my_app')

# Set request context
set_request_context(user_id='123', request_path='/api/test')

# Log messages
logger.info("Operation started", operation='test')
logger.debug("Debug info", data={'key': 'value'})
logger.warning("Something suspicious", ip='1.2.3.4')
logger.error("Operation failed", error='Connection timeout')
```

---

## 📖 API Reference

### `get_logger(name: str, app_name: str = None) -> AppLogger`

Get a logger instance.

```python
logger = get_logger(__name__)
logger = get_logger(__name__, app_name='my_app')
```

### `set_request_context(**kwargs)`

Set context added to all log entries.

```python
set_request_context(
    user_id='user_123',
    request_path='/api/generate',
    request_id='req_456',
    trace_id='trace_789'
)
```

### `clear_request_context()`

Clear the current request context.

```python
clear_request_context()
```

### `get_request_context() -> dict`

Get the current context.

```python
context = get_request_context()
```

---

## 📊 Log Levels

```python
logger.debug("Detailed debug info")      # DEBUG
logger.info("Normal operations")          # INFO
logger.warning("Warning conditions")      # WARNING
logger.error("Error conditions")          # ERROR
logger.critical("Critical failures")      # CRITICAL
```

---

## 🏷️ Log Categories

```python
from shared.logging import LogCategory, set_log_category

# Available categories
LogCategory.API       # API requests
LogCategory.AUTH      # Authentication
LogCategory.DATABASE  # Database operations
LogCategory.PAYMENT   # Payment processing
LogCategory.GENERATION # AI generations

# Set category for current context
set_log_category(LogCategory.API)
```

---

## ⏱️ Timing Utilities

### Timer Context Manager

```python
from shared.logging import Timer

with Timer() as t:
    do_something()

logger.info(f"Operation took {t.duration_ms}ms")
```

### Duration Logging

```python
from shared.logging import log_duration

@log_duration('generate_image')
def generate_image(prompt):
    # Automatically logs duration on completion
    pass
```

---

## 📋 Structured Logging Format

Logs are output as JSON for easy parsing:

```json
{
    "timestamp": "2026-02-01T10:30:00.000Z",
    "level": "INFO",
    "logger": "backend.routes.generate",
    "message": "Generation completed",
    "user_id": "user_123",
    "request_path": "/api/generate",
    "model": "flux-dev",
    "duration_ms": 1234,
    "credits_used": 10
}
```

---

## 🔒 Sensitive Data Filtering

Sensitive fields are automatically redacted:

```python
logger.info("User action", 
    password="secret123",      # Redacted: ***REDACTED***
    api_key="sk_live_xxx",     # Redacted: ***REDACTED***
    token="eyJhbG...",         # Redacted: ***REDACTED***
    email="user@example.com"   # Preserved (not in default filter)
)
```

### Configure Sensitive Patterns

```yaml
# config.yaml
logging:
  sensitive_patterns:
    - password
    - api_key
    - token
    - secret
    - authorization
```

---

## 🔧 Flask Integration

```python
from flask import Flask, request, g
from shared.logging import get_logger, set_request_context, clear_request_context
import uuid

app = Flask(__name__)
logger = get_logger(__name__)

@app.before_request
def before_request():
    g.request_id = str(uuid.uuid4())
    set_request_context(
        request_id=g.request_id,
        request_path=request.path,
        method=request.method
    )
    logger.info("Request started")

@app.after_request
def after_request(response):
    logger.info("Request completed", status=response.status_code)
    clear_request_context()
    return response

@app.errorhandler(Exception)
def handle_error(error):
    logger.error("Unhandled exception", 
        error=str(error),
        exc_info=True
    )
    return {'error': 'Internal server error'}, 500
```

---

## ⚙️ Configuration

### config.yaml

```yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: json  # json or text
  
  outputs:
    - console
    - file
  
  file:
    path: logs/app.log
    max_size_mb: 10
    backup_count: 5
  
  include_context: true
  
  sensitive_patterns:
    - password
    - api_key
    - token
    - secret
    - key
    - authorization
```

### Environment Variables

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 🕐 Timestamp Utilities

Avoid timezone bugs with these utilities:

```python
from shared.logging import get_epoch_ms, get_epoch_seconds, get_utc_iso

# Get current time as epoch milliseconds
epoch_ms = get_epoch_ms()  # 1706789400000

# Get current time as epoch seconds
epoch_sec = get_epoch_seconds()  # 1706789400

# Get current time as ISO string
iso = get_utc_iso()  # "2026-02-01T10:30:00.000Z"
```

---

## 📚 Related Documentation

- [TELEMETRY.md](TELEMETRY.md) - Event tracking
- [ANALYTICS.md](ANALYTICS.md) - Analytics integration
