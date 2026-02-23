# Umami Analytics Module

A **privacy-first, universal analytics module** for Python backends and React frontends. Designed to be reusable, configurable, and safe.

## Privacy Guarantee

This module **ONLY sends text-based events and metrics**:

- ❌ NO screenshots
- ❌ NO session recordings
- ❌ NO DOM captures
- ❌ NO raw user data
- ✅ ALL PII is automatically sanitized before transmission

## Features

| Feature | Description |
|---------|-------------|
| **Async Event Queue** | Non-blocking event sending with batching |
| **PII Sanitization** | Emails, UUIDs, tokens, API keys automatically redacted |
| **Flask Integration** | Middleware for automatic request tracking |
| **Request Context** | Forward client IP, user-agent for attribution |
| **Configurable** | YAML config + environment variables |
| **Graceful Degradation** | No crashes if analytics is disabled |
| **React Hook** | Works with web browsers and Capacitor mobile apps |

## Quick Start

### Python Backend

```python
from shared.analytics import get_analytics, track_event

# Option 1: Get instance
analytics = get_analytics('my_app')
analytics.track_event('signup', {'plan': 'pro'})
analytics.track_page_view('/dashboard')

# Option 2: Quick functions
track_event('button_click', {'button': 'submit'})

# Option 3: Flask integration
from flask import Flask
app = Flask(__name__)
analytics.init_flask(app)  # Auto-tracks all requests
```

### React Frontend

```jsx
import { useAnalytics } from '@/lib/analytics';

function MyComponent() {
  const { trackEvent, trackPageView } = useAnalytics();
  
  useEffect(() => {
    trackPageView('/dashboard');
  }, []);
  
  const handleClick = () => {
    trackEvent('button_click', { button: 'submit' });
  };
  
  return <button onClick={handleClick}>Submit</button>;
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `UMAMI_WEBSITE_ID` | Yes | - | Your Umami website ID |
| `UMAMI_API_URL` | No | `https://cloud.umami.is` | Umami API endpoint |
| `UMAMI_API_KEY` | No | - | API key for authenticated requests |
| `UMAMI_HOSTNAME` | No | app_name | Override hostname in events |
| `UMAMI_ENABLED` | No | `true` | Enable/disable analytics |
| `UMAMI_DEBUG` | No | `false` | Enable debug logging |

### Backend (.env)

```bash
UMAMI_WEBSITE_ID=f3d5a649-61eb-462a-846e-fced3988e820
UMAMI_API_URL=https://cloud.umami.is
UMAMI_API_KEY=your_api_key_here
UMAMI_ENABLED=true
```

### Frontend (Vite .env)

```bash
VITE_UMAMI_WEBSITE_ID=f3d5a649-61eb-462a-846e-fced3988e820
VITE_UMAMI_API_URL=https://cloud.umami.is
VITE_UMAMI_DEBUG=false
```

## PII Sanitization

All URLs and data are automatically sanitized before transmission:

| PII Type | Example | Result |
|----------|---------|--------|
| Email | `john@example.com` | `[REDACTED_EMAIL]` |
| UUID | `550e8400-e29b-...` | `[REDACTED_UUID]` |
| JWT Token | `eyJhbGci...` | `[REDACTED_TOKEN]` |
| API Key | `sk_live_123...` | `[REDACTED_KEY]` |
| Phone | `555-123-4567` | `[REDACTED_PHONE]` |
| Credit Card | `4111-1111-...` | `[REDACTED_CARD]` |

### Manual Sanitization

```python
from shared.analytics import sanitize_url, sanitize_data, is_pii_detected

# Sanitize a URL
clean = sanitize_url('/user/john@example.com/reset?token=abc')
# Result: '/user/[REDACTED_EMAIL]/reset?token=[REDACTED]'

# Sanitize data object
clean = sanitize_data({'email': 'user@test.com', 'action': 'login'})
# Result: {'email': '[REDACTED_EMAIL]', 'action': 'login'}

# Check for PII
if is_pii_detected(user_input):
    print("Warning: PII detected!")
```

## Flask Integration

```python
from flask import Flask
from shared.analytics import get_analytics

app = Flask(__name__)
analytics = get_analytics('my_app')

# Auto-track all requests with timing
analytics.init_flask(app)

# Or use decorator for specific routes
from shared.analytics import track_route

@app.route('/api/generate')
@track_route(analytics, 'image_generation')
def generate():
    return {'status': 'ok'}
```

### Configuration (config.yaml)

```yaml
flask:
  auto_track_requests: true
  track_timing: true
  track_errors: true
  exclude_paths:
    - /health
    - /metrics
    - /static
```

## Async Queue

Events are sent asynchronously by default to avoid blocking:

```python
# Events are queued and sent in batches
analytics.track_event('action', {'key': 'value'})  # Returns immediately

# Force flush on shutdown
analytics.flush()
analytics.shutdown()
```

### Configuration

```yaml
async:
  enabled: true
  batch_size: 10
  flush_interval: 5.0  # seconds
  max_queue_size: 1000
```

## React Hook Details

The hook automatically detects the platform:

| Platform | Method |
|----------|--------|
| Web (with Umami script) | Uses `window.umami` |
| Web (fallback) | Direct API call |
| Capacitor mobile | Direct API call |
| SSR | Safe no-op |

```jsx
const { 
  trackEvent,      // Track custom events
  trackPageView,   // Track page views (web)
  trackScreenView, // Track screen views (mobile)
  trackError,      // Track errors
  trackTiming,     // Track timing/performance
  sanitizeUrl,     // Manual sanitization
  isEnabled,       // Check if analytics is enabled
  isCapacitor,     // Check if running in Capacitor
} = useAnalytics();
```

## Files

```
shared/analytics/
├── __init__.py      # Exports all public functions
├── config.yaml      # Default configuration
├── umami.py         # UmamiAnalytics class
├── sanitizer.py     # PII sanitization utilities
└── README.md        # This file

frontend/src/lib/
└── analytics.js     # React hook
```

## Testing

```bash
cd applications/asaad_000_MultiImageGenerator/backend
poetry run python test_analytics.py
```

Tests cover:
- All PII sanitization patterns
- Async event queuing
- Flask integration
- Configuration loading
- Thread safety
- Graceful degradation

## License

MIT
