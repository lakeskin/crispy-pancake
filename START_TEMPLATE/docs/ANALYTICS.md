# 📊 Analytics Module (Umami)

Privacy-first analytics integration with Umami.

---

## 📦 Module Structure

```
shared/analytics/
├── __init__.py       # Public exports
├── umami.py          # Umami client
├── sanitizer.py      # PII sanitization
└── config.yaml       # Analytics configuration
```

---

## 🔒 Privacy Guarantee

This module:
- ✅ ONLY sends text-based events and metrics
- ✅ NO screenshots, session recordings, or DOM captures
- ✅ ALL PII is automatically sanitized before transmission
- ✅ URLs are cleaned of emails, tokens, and sensitive data

---

## 🚀 Quick Start

```python
from shared.analytics import get_analytics, track_event

# Get analytics instance
analytics = get_analytics('my_app')

# Track events
analytics.track_event('signup', {'plan': 'pro'})
analytics.track_page_view('/dashboard')

# Flask integration (auto-tracks all routes)
analytics.init_flask(app)
```

---

## 📖 API Reference

### `get_analytics(app_name: str) -> UmamiAnalytics`

Get or create analytics instance.

```python
analytics = get_analytics('my_app')
```

### `track_event(event_name: str, properties: dict)`

Track a custom event.

```python
track_event('button_click', {'button': 'submit', 'page': '/signup'})
```

### `track_page_view(path: str)`

Track a page view.

```python
track_page_view('/dashboard')
```

### `track_route` (Decorator)

Automatically track route access.

```python
from shared.analytics import track_route

@app.route('/api/generate')
@track_route('api.generate')
def generate():
    pass
```

---

## 🧹 PII Sanitization

The module automatically sanitizes:
- Email addresses
- UUIDs
- JWT tokens
- API keys
- Phone numbers
- Credit card numbers
- Long hex strings

### Manual Sanitization

```python
from shared.analytics import sanitize_url, sanitize_data, is_pii_detected

# Clean a URL
clean_url = sanitize_url('/user/john@example.com/reset?token=abc123')
# Result: '/user/[REDACTED_EMAIL]/reset?token=[REDACTED]'

# Sanitize data
clean_data = sanitize_data({'email': 'user@test.com', 'action': 'login'})
# Result: {'email': '[REDACTED_EMAIL]', 'action': 'login'}

# Check for PII
if is_pii_detected(user_input):
    logger.warning("PII detected in input!")
```

---

## ⚙️ Configuration

### Environment Variables

```bash
UMAMI_WEBSITE_ID=your-website-id    # Required
UMAMI_API_URL=https://cloud.umami.is
UMAMI_API_KEY=your-api-key          # Optional
UMAMI_ENABLED=true
UMAMI_DEBUG=false
```

### config.yaml

```yaml
umami:
  enabled: true
  website_id: ${UMAMI_WEBSITE_ID}
  api_url: ${UMAMI_API_URL}
  
  sanitization:
    enabled: true
    sanitize_emails: true
    sanitize_tokens: true
    sanitize_api_keys: true
    sanitize_uuids: true
  
  async:
    enabled: true
    queue_size: 1000
    batch_size: 10
    flush_interval_seconds: 5
```

---

## 🔧 Flask Integration

```python
from flask import Flask
from shared.analytics import get_analytics

app = Flask(__name__)
analytics = get_analytics('my_app')

# Initialize Flask middleware
analytics.init_flask(app)

# All routes automatically tracked with:
# - Request path
# - HTTP method
# - Response status
# - Request duration
```

---

## 📊 Common Events to Track

```python
# User lifecycle
track_event('signup', {'source': 'homepage', 'plan': 'free'})
track_event('login', {'method': 'email'})
track_event('logout', {})

# Feature usage
track_event('generation.started', {'model': 'flux-dev'})
track_event('generation.completed', {'credits_used': 10})
track_event('export.downloaded', {'format': 'png'})

# Commerce
track_event('checkout.started', {'package': 'creator'})
track_event('purchase.completed', {'package': 'creator', 'amount': 9.99})
track_event('subscription.started', {'plan': 'pro_monthly'})

# Errors (without sensitive data)
track_event('error.api', {'endpoint': '/generate', 'status': 500})
```

---

## 📚 Related Documentation

- [TELEMETRY.md](TELEMETRY.md) - Unified telemetry
- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - Environment configuration
