# 🤖 COPILOT INSTRUCTIONS - START TEMPLATE

> **MANDATORY READING FOR ALL AI ASSISTANTS**
>
> This document defines the REQUIRED patterns and rules when working with applications built from this template. **These are not suggestions - they are requirements.**

---

## 🎯 CORE PRINCIPLES (MEMORIZE THESE)

### 1. ⚙️ CONFIGURABILITY - "Nothing Hardcoded"

**EVERY** configurable value MUST be in a YAML file, NOT in Python code.

```yaml
# ✅ CORRECT: Config in YAML
# config.yaml
pricing:
  starter_pack:
    credits: 50
    price: 4.99

# ❌ WRONG: Hardcoded in Python
# DO NOT DO THIS
STARTER_CREDITS = 50
STARTER_PRICE = 4.99
```

**What goes in YAML:**
- All pricing and packages
- All text strings shown to users
- All feature flags
- All numeric thresholds
- All model names
- All retry/timeout values

### 2. 🔄 REUSABILITY - "Write Once, Use Everywhere"

**ALWAYS** use shared modules. **NEVER** write duplicate functionality.

```python
# ✅ CORRECT: Use shared auth
from shared.auth import require_auth, get_current_user

@app.route('/api/protected')
@require_auth
def protected_route():
    user = get_current_user()
    return {'message': f'Hello {user["email"]}'}

# ❌ WRONG: Writing your own auth
def my_verify_token(token):  # DON'T DO THIS!
    # Custom JWT verification...
```

### 3. 🔐 SECURITY - "Secrets in Environment, Never in Code"

**NEVER** put credentials or API keys in code or config files.

```python
# ✅ CORRECT: Use environment variables
import os
api_key = os.getenv('STRIPE_SECRET_KEY')

# ❌ WRONG: Hardcoded secrets
api_key = 'sk_live_abc123'  # NEVER DO THIS!
```

### 4. 📊 OBSERVABILITY - "Track Everything"

**ALWAYS** use telemetry and logging for important operations.

```python
# ✅ CORRECT: Use telemetry
from shared.telemetry import track, track_duration

@track_duration('generation')
def generate_image(prompt):
    track('generation.started', model='flux', user_id=user_id)
    result = do_generation()
    track('generation.completed', credits_used=10)
    return result

# ❌ WRONG: No tracking
def generate_image(prompt):
    return do_generation()  # No visibility!
```

---

## 📦 SHARED MODULES - REQUIRED USAGE

### Authentication (`shared/auth/`)

**ALWAYS use for:**
- Route protection
- Token verification
- User context

**Available exports:**
```python
from shared.auth import (
    require_auth,      # Decorator: requires valid token
    optional_auth,     # Decorator: auth optional but captured
    require_role,      # Decorator: requires specific role
    get_current_user,  # Get authenticated user from context
    get_auth_provider, # Get auth provider instance
)
```

**Example patterns:**
```python
# Protected route
@app.route('/api/me')
@require_auth
def get_profile():
    user = get_current_user()
    return jsonify(user)

# Optional auth
@app.route('/api/public')
@optional_auth
def public_route():
    user = get_current_user()
    if user:
        return {'greeting': f'Hello, {user["email"]}'}
    return {'greeting': 'Hello, guest'}

# Role-based access
@app.route('/api/admin')
@require_role(['admin', 'moderator'])
def admin_route():
    return {'message': 'Admin area'}
```

### Credits (`shared/credits/`)

**ALWAYS use for:**
- Balance checking
- Credit deduction
- Credit addition
- Transaction history

**Available exports:**
```python
from shared.credits import (
    get_credit_manager,          # Factory for manager
    CreditManager,               # Base class
    InsufficientCreditsError,    # Exception
    get_pricing_service,         # Pricing calculations
    get_stripe_service,          # Stripe integration
)
```

**Example patterns:**
```python
manager = get_credit_manager()

# Check balance
balance = manager.get_balance(user_id)

# Check before deducting
if manager.check_sufficient_credits(user_id, cost):
    transaction = manager.deduct_credits(
        user_id=user_id,
        amount=cost,
        description="Image generation",
        metadata={'model': 'flux-dev', 'prompt': prompt[:100]}
    )
else:
    raise InsufficientCreditsError(required=cost, available=balance.credits)
```

### Analytics (`shared/analytics/`)

**ALWAYS use for:**
- Page views
- User events
- Feature usage

**Available exports:**
```python
from shared.analytics import (
    get_analytics,     # Get analytics instance
    track_event,       # Track custom event
    track_page_view,   # Track page view
    track_route,       # Decorator for route tracking
    sanitize_url,      # Clean PII from URLs
)
```

**Example patterns:**
```python
analytics = get_analytics('my_app')

# Track events
analytics.track_event('signup', {'plan': 'pro', 'source': 'homepage'})
analytics.track_page_view('/dashboard')

# With Flask middleware (auto-tracks all routes)
analytics.init_flask(app)
```

### Telemetry (`shared/telemetry/`)

**ALWAYS use for:**
- Operation timing
- Event tracking across systems

**Available exports:**
```python
from shared.telemetry import (
    track,             # Track event
    track_event,       # Alias for track
    track_duration,    # Decorator for timing
    track_function,    # Decorator with more options
    Telemetry,         # Tracker class
)
```

**Example patterns:**
```python
# Simple tracking
track('generation.started', model='flux', user_id=user_id)

# Timing decorator
@track_duration('api.generate')
def generate():
    # Code here
    pass

# Context tracking
telemetry = Telemetry.get_instance()
telemetry.set_context(user_id=user_id, session_id=session_id)
```

### Logging (`shared/logging/`)

**ALWAYS use for:**
- Structured logging
- Error tracking
- Request context

**Available exports:**
```python
from shared.logging import (
    get_logger,              # Get logger instance
    set_request_context,     # Set request context
    clear_request_context,   # Clear context
    LogCategory,             # Log categories
    Timer,                   # Timing utility
    log_duration,            # Duration logging
)
```

**Example patterns:**
```python
logger = get_logger(__name__, app_name='my_app')

# Log with context
set_request_context(user_id=user_id, request_path='/api/generate')
logger.info("Generation started", model='flux', credits_cost=10)

# Log errors with stack trace
try:
    result = do_something()
except Exception as e:
    logger.error("Operation failed", error=str(e), exc_info=True)
    raise
```

### Admin Panel (`shared/admin/`)

**ALWAYS use for:**
- Config file management (YAML/JSON)
- Admin panel endpoints
- Backup and restore
- Settings UI

**Available exports:**
```python
from shared.admin import (
    ConfigManager,         # Core YAML/JSON operations
    BackupManager,         # Backup/restore functionality
    create_admin_router,   # FastAPI router factory
    # Pydantic models
    ConfigDefinition,
    ConfigListItem,
    ConfigResponse,
    SaveConfigResponse,
    BackupItem,
)
```

**Backend example:**
```python
from shared.admin import create_admin_router
from shared.auth.decorators import require_admin

# Define your configs
CONFIG_DEFINITIONS = {
    'backend': {
        'path': 'config.yaml',
        'name': 'Backend Config',
        'description': 'Main settings',
        'category': 'core'
    },
    'theme': {
        'path': 'theme.json',
        'name': 'Theme',
        'category': 'ui'
    }
}

# One-liner to create all admin endpoints
admin_router = create_admin_router(
    config_definitions=CONFIG_DEFINITIONS,
    require_admin=require_admin,  # ALWAYS protect!
)
app.include_router(admin_router)
```

**Frontend example:**
```tsx
import { ConfigEditor, BackupManager } from './components/admin';
import { useConfig } from './hooks/useConfig';

// Config editor component
<ConfigEditor configId="backend" title="Backend Settings" />

// Section-specific editor
<ConfigEditor configId="theme" sectionPath="fonts" title="Fonts" />

// Backup manager
<BackupManager />

// React hook
const { data, save, loading, isDirty } = useConfig('backend');
```

**⚠️ CRITICAL: Always protect admin routes!**
```python
# ✅ CORRECT - Protected
create_admin_router(config_definitions, require_admin=require_admin)

# ❌ WRONG - Unprotected (anyone can modify configs!)
create_admin_router(config_definitions, require_admin=None)
```

---

## 🚫 FORBIDDEN PATTERNS

### 1. NEVER Write Duplicate Auth Logic

```python
# ❌ FORBIDDEN
def verify_token_manually(token):
    decoded = jwt.decode(token, SECRET_KEY)
    return decoded

# ❌ FORBIDDEN
def get_user_from_header():
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1]
    # ...
```

### 2. NEVER Hardcode Credentials

```python
# ❌ FORBIDDEN
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
STRIPE_KEY = "sk_live_abc123..."

# ❌ FORBIDDEN (even in config files)
# config.yaml
api_key: "sk_live_abc123"
```

### 3. NEVER Skip Credit Checks

```python
# ❌ FORBIDDEN - deducting without checking
@require_auth
def generate():
    user = get_current_user()
    do_expensive_operation()
    manager.deduct_credits(user['id'], 100)  # What if they don't have 100?
```

### 4. NEVER Ignore Errors

```python
# ❌ FORBIDDEN
try:
    manager.deduct_credits(user_id, cost)
except:
    pass  # NEVER silently swallow errors!
```

### 5. NEVER Expose Internal Data

```python
# ❌ FORBIDDEN
@app.route('/api/debug')
def debug():
    return jsonify({
        'env': dict(os.environ),  # Exposes secrets!
        'all_users': get_all_users()  # Data leak!
    })
```

---

## ✅ REQUIRED PATTERNS

### 1. Route Protection Pattern

```python
from flask import Flask, jsonify, request
from shared.auth import require_auth, get_current_user
from shared.credits import get_credit_manager
from shared.telemetry import track, track_duration
from shared.logging import get_logger

app = Flask(__name__)
logger = get_logger(__name__)
credit_manager = get_credit_manager()

@app.route('/api/generate', methods=['POST'])
@require_auth
@track_duration('api.generate')
def generate():
    user = get_current_user()
    data = request.json
    
    # 1. Validate input
    if not data.get('prompt'):
        return {'error': 'Prompt required'}, 400
    
    # 2. Check credits
    cost = 10
    if not credit_manager.check_sufficient_credits(user['id'], cost):
        track('generation.insufficient_credits', user_id=user['id'])
        return {'error': 'Insufficient credits'}, 402
    
    # 3. Track start
    track('generation.started', user_id=user['id'], model='flux')
    
    try:
        # 4. Do the work
        result = do_generation(data['prompt'])
        
        # 5. Deduct credits
        credit_manager.deduct_credits(
            user['id'], 
            cost, 
            "Image generation",
            {'model': 'flux', 'prompt_preview': data['prompt'][:50]}
        )
        
        # 6. Track success
        track('generation.completed', user_id=user['id'], credits_used=cost)
        
        return {'success': True, 'result': result}
        
    except Exception as e:
        # 7. Track and log failure
        track('generation.failed', user_id=user['id'], error=str(e))
        logger.error("Generation failed", user_id=user['id'], error=str(e))
        return {'error': 'Generation failed'}, 500
```

### 2. Config Loading Pattern

```python
import yaml
from pathlib import Path

def load_config(config_name: str = 'config.yaml'):
    """Load YAML configuration"""
    config_path = Path(__file__).parent / config_name
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Use config for all variable values
config = load_config()
MODEL_COSTS = config['models']  # From YAML, not hardcoded
```

### 3. Error Handling Pattern

```python
from shared.credits.exceptions import InsufficientCreditsError

@app.route('/api/action', methods=['POST'])
@require_auth
def action():
    user = get_current_user()
    
    try:
        result = perform_action(user['id'])
        return {'success': True, 'result': result}
        
    except InsufficientCreditsError as e:
        logger.warning("Insufficient credits", 
                      user_id=user['id'], 
                      required=e.required, 
                      available=e.available)
        return {
            'error': 'Insufficient credits',
            'required': e.required,
            'available': e.available
        }, 402
        
    except ValidationError as e:
        return {'error': str(e)}, 400
        
    except Exception as e:
        logger.error("Unexpected error", user_id=user['id'], error=str(e))
        return {'error': 'Internal server error'}, 500
```

---

## 🔧 CONFIGURATION FILES

### Required Config Files

1. **`config.yaml`** - Main application config
2. **`shared/auth/config.yaml`** - Auth configuration
3. **`shared/credits/config.yaml`** - Pricing and credit config
4. **`logging.yaml`** - Logging configuration

### Config Structure Example

```yaml
# config.yaml
app:
  name: "My Application"
  version: "1.0.0"
  debug: false

models:
  flux-schnell:
    cost: 5
    description: "Fast image generation"
  flux-dev:
    cost: 10
    description: "High quality generation"

features:
  video_generation: false
  premium_models: true

generation:
  max_prompt_length: 1000
  default_image_size: "1024x1024"
```

---

## 📋 CHECKLIST FOR NEW CODE

Before submitting code, verify:

- [ ] Using `@require_auth` decorator for protected routes
- [ ] Using `get_current_user()` to get user data
- [ ] Using `get_credit_manager()` for credit operations
- [ ] Checking credits BEFORE expensive operations
- [ ] Using `track()` for important events
- [ ] Using `logger` for errors and important info
- [ ] All config values from YAML, not hardcoded
- [ ] No credentials in code
- [ ] Proper error handling with specific exceptions
- [ ] Response includes appropriate error messages

---

## 📚 REFERENCE

### Import Cheat Sheet

```python
# Authentication
from shared.auth import require_auth, optional_auth, require_role, get_current_user

# Credits
from shared.credits import get_credit_manager, get_pricing_service, get_stripe_service
from shared.credits.exceptions import InsufficientCreditsError

# Analytics
from shared.analytics import get_analytics, track_event, track_page_view

# Telemetry
from shared.telemetry import track, track_duration

# Logging
from shared.logging import get_logger, set_request_context
```

### Common Operations

```python
# Get authenticated user
user = get_current_user()
user_id = user['id']
email = user['email']

# Check and deduct credits
manager = get_credit_manager()
balance = manager.get_balance(user_id)
if balance.credits >= cost:
    manager.deduct_credits(user_id, cost, "Description")

# Create Stripe checkout
stripe_svc = get_stripe_service()
result = stripe_svc.create_package_checkout(...)

# Track event
track('event.name', property1='value1', property2='value2')

# Log with context
logger = get_logger(__name__)
logger.info("Message", key='value')
```

---

**REMEMBER: Consistency is key. Follow these patterns exactly to maintain a coherent, maintainable codebase.**
