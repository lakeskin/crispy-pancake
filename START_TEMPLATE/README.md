# 🚀 START TEMPLATE - Reusable Application Framework

> **Version**: 1.0  
> **Created**: February 2026  
> **Based On**: AsaadAshProjects Shared Modules

This template contains battle-tested, production-ready components for building new applications quickly. Every module here has been refined through real-world usage.

---

## 📋 TABLE OF CONTENTS

1. [Quick Start](#-quick-start)
2. [What's Included](#-whats-included)
3. [Architecture](#-architecture)
4. [Module Overview](#-module-overview)
5. [Environment Setup](#-environment-setup)
6. [Integration Guide](#-integration-guide)
7. [Best Practices](#-best-practices)

---

## 🚀 QUICK START

### 1. Copy Template to Your New App

```bash
# Copy the template to your new application
cp -r START_TEMPLATE applications/your_new_app_name

# Navigate to your new app
cd applications/your_new_app_name
```

### 2. Install Dependencies

```bash
# Backend (Python)
poetry install

# Frontend (if applicable)
cd frontend && npm install
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.template .env

# Fill in your credentials
# See ENVIRONMENT_SETUP.md for details
```

### 4. Run Your Application

```bash
# Backend
poetry run uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

---

## 📦 WHAT'S INCLUDED

### Backend Modules (Python)

| Module | Description | Documentation |
|--------|-------------|---------------|
| `shared/auth/` | Authentication with Supabase | [AUTH.md](docs/AUTH.md) |
| `shared/credits/` | Credit system with Stripe | [CREDITS.md](docs/CREDITS.md) |
| `shared/payments/` | Payment tracking | [PAYMENTS.md](docs/PAYMENTS.md) |
| `shared/analytics/` | Umami analytics integration | [ANALYTICS.md](docs/ANALYTICS.md) |
| `shared/telemetry/` | Event tracking | [TELEMETRY.md](docs/TELEMETRY.md) |
| `shared/logging/` | Centralized logging | [LOGGING.md](docs/LOGGING.md) |
| `shared/database/` | Database utilities | [DATABASE.md](docs/DATABASE.md) |
| `shared/admin/` | **🆕 Admin config management** | [ADMIN.md](docs/ADMIN.md) |

### Frontend Modules (TypeScript/React)

| Module | Description |
|--------|-------------|
| `frontend/src/services/authStorage.ts` | Token persistence with Remember Me |
| `frontend/src/services/adminApi.ts` | **🆕 Admin API client** |
| `frontend/src/contexts/AuthContext.tsx` | React auth context |
| `frontend/src/hooks/useConfig.ts` | **🆕 Config state hooks** |
| `frontend/src/components/auth/` | Auth UI components |
| `frontend/src/components/credits/` | Credit purchase components |
| `frontend/src/components/admin/` | **🆕 Admin panel components** |
| `frontend/src/ThemeProvider.tsx` | Dynamic theming system |

---

## 🏗️ ARCHITECTURE

```
your_new_app/
├── backend/
│   ├── shared/                 # ⭐ REUSABLE MODULES (copy from here)
│   │   ├── auth/              # Authentication
│   │   ├── credits/           # Credit management
│   │   ├── payments/          # Payment tracking
│   │   ├── analytics/         # Umami analytics
│   │   ├── telemetry/         # Event tracking
│   │   ├── logging/           # Centralized logging
│   │   ├── database/          # DB utilities
│   │   └── admin/             # 🆕 Config management & admin panel
│   ├── routes/                # Your API routes
│   ├── services/              # Your business logic
│   └── main.py                # App entry point
├── frontend/
│   ├── src/
│   │   ├── services/          # API and auth services
│   │   ├── contexts/          # React contexts
│   │   ├── hooks/             # 🆕 Custom hooks (useConfig, etc.)
│   │   ├── components/        # UI components
│   │   │   ├── auth/          # Auth modals
│   │   │   ├── credits/       # Credit purchase
│   │   │   └── admin/         # 🆕 Admin panel components
│   │   ├── pages/             # Page components
│   │   └── ThemeProvider.tsx  # Theme system
│   └── package.json
├── docs/                      # Module documentation
├── .env.template              # Environment template
└── pyproject.toml             # Python dependencies
```

---

## 🔧 MODULE OVERVIEW

### 1. Authentication (`shared/auth/`)

**Features:**
- ✅ Supabase JWT authentication
- ✅ Token verification (local JWT + API fallback)
- ✅ Flask decorators (`@require_auth`, `@optional_auth`, `@require_role`)
- ✅ Remember Me functionality
- ✅ Automatic token refresh

**Key Files:**
```
shared/auth/
├── __init__.py           # Public exports
├── base.py               # Abstract AuthProvider interface
├── supabase.py           # Supabase implementation
├── decorators.py         # Flask route decorators
├── config.yaml           # Auth configuration
└── authStorage.js        # Frontend token storage
```

**Usage:**
```python
from shared.auth import require_auth, get_current_user

@app.route('/api/protected')
@require_auth
def protected_route():
    user = get_current_user()
    return {'message': f'Hello {user["email"]}'}
```

### 2. Credit System (`shared/credits/`)

**Features:**
- ✅ Provider-agnostic credit management
- ✅ Stripe integration for payments
- ✅ Config-driven pricing (YAML)
- ✅ Coupons and subscriptions
- ✅ Transaction history

**Key Files:**
```
shared/credits/
├── __init__.py           # Factory functions
├── base.py               # Abstract CreditManager
├── models.py             # Data models (Pydantic)
├── config.yaml           # Pricing configuration
├── pricing_service.py    # Price calculations
├── stripe_service.py     # Stripe integration
├── providers/
│   └── supabase.py       # Supabase implementation
└── exceptions.py         # Custom exceptions
```

**Usage:**
```python
from shared.credits import get_credit_manager

manager = get_credit_manager()
balance = manager.get_balance(user_id)

if manager.check_sufficient_credits(user_id, 10):
    manager.deduct_credits(user_id, 10, "Generated image")
```

### 3. Analytics (`shared/analytics/`)

**Features:**
- ✅ Umami privacy-first analytics
- ✅ Automatic PII sanitization
- ✅ Flask middleware integration
- ✅ Async event queue

**Usage:**
```python
from shared.analytics import get_analytics, track_event

analytics = get_analytics('my_app')
analytics.track_event('signup', {'plan': 'pro'})
analytics.track_page_view('/dashboard')
```

### 4. Telemetry (`shared/telemetry/`)

**Features:**
- ✅ Unified event tracking
- ✅ Routes to Umami + logging
- ✅ Decorators for timing

**Usage:**
```python
from shared.telemetry import track, track_duration

track('generation.started', model='flux-schnell', user_id='123')

@track_duration('generation')
def generate_image(prompt):
    # Your code here
    pass
```

### 5. Logging (`shared/logging/`)

**Features:**
- ✅ Structured JSON logging
- ✅ Request context tracking
- ✅ Sensitive data filtering
- ✅ New Relic integration

**Usage:**
```python
from shared.logging import get_logger, set_request_context

logger = get_logger(__name__, app_name='my_app')
set_request_context(user_id='123', request_path='/api/test')

logger.info("Operation started", operation='test')
```

### 6. Admin Panel (`shared/admin/`) 🆕

**Features:**
- ✅ YAML/JSON config file management
- ✅ Dot-notation access (`appearance.fonts.heading`)
- ✅ Automatic backups before every save
- ✅ FastAPI router factory - one line to add all endpoints
- ✅ Search across all configs
- ✅ Backup restore and cleanup
- ✅ Hot-reload support

**Backend Usage:**
```python
from shared.admin import create_admin_router
from shared.auth.decorators import require_admin

# Define your config files
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
        'description': 'UI appearance',
        'category': 'ui'
    }
}

# Create router with CRUD endpoints
admin_router = create_admin_router(
    config_definitions=CONFIG_DEFINITIONS,
    require_admin=require_admin,
    prefix="/api/admin"
)
app.include_router(admin_router)
```

**Frontend Usage:**
```tsx
import { ConfigEditor, BackupManager } from './components/admin';
import { useConfig } from './hooks/useConfig';

// Full config editor
<ConfigEditor configId="backend" title="Backend Settings" />

// Edit specific section
<ConfigEditor configId="theme" sectionPath="appearance.fonts" />

// Backup management
<BackupManager />

// React hook
const { data, save, isDirty } = useConfig('backend');
```

**Generated Endpoints:**
- `GET /api/admin/configs` - List all configs
- `GET/PUT /api/admin/configs/{id}` - Full config CRUD
- `GET/PUT /api/admin/configs/{id}/{path}` - Section CRUD
- `GET /api/admin/configs/search?q=...` - Search
- `POST /api/admin/configs/reload` - Hot-reload
- `GET/POST/DELETE /api/admin/backups/*` - Backup management

📖 **Full documentation:** [ADMIN.md](docs/ADMIN.md)

---

## 🔐 ENVIRONMENT SETUP

See [ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md) for complete details.

### Required Environment Variables

```bash
# Supabase (Authentication + Database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
SUPABASE_JWT_SECRET=your_jwt_secret

# Stripe (Payments)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Analytics (Umami)
UMAMI_WEBSITE_ID=your_website_id
UMAMI_API_URL=https://cloud.umami.is
```

---

## 🎯 INTEGRATION GUIDE

### Adding Auth to a New Route

```python
from flask import Flask, jsonify
from shared.auth import require_auth, get_current_user

app = Flask(__name__)

@app.route('/api/me')
@require_auth
def get_profile():
    user = get_current_user()
    return jsonify(user)
```

### Adding Credit Checks

```python
from shared.credits import get_credit_manager
from shared.credits.exceptions import InsufficientCreditsError

manager = get_credit_manager()

@app.route('/api/generate', methods=['POST'])
@require_auth
def generate():
    user = get_current_user()
    cost = 10  # credits
    
    if not manager.check_sufficient_credits(user['id'], cost):
        return {'error': 'Insufficient credits'}, 402
    
    # Do the work...
    
    manager.deduct_credits(user['id'], cost, "Image generation")
    return {'success': True}
```

### Adding Stripe Checkout

```python
from shared.credits import get_stripe_service

stripe_service = get_stripe_service()

@app.route('/api/checkout', methods=['POST'])
@require_auth
def create_checkout():
    user = get_current_user()
    data = request.json
    
    result = stripe_service.create_package_checkout(
        user_id=user['id'],
        user_email=user['email'],
        package_id=data['package_id'],
        success_url='https://yourapp.com/success',
        cancel_url='https://yourapp.com/cancel'
    )
    
    return {'checkout_url': result.checkout_url}
```

---

## ✅ BEST PRACTICES

### 1. Always Use Shared Modules
```python
# ✅ GOOD: Use shared modules
from shared.auth import require_auth
from shared.credits import get_credit_manager

# ❌ BAD: Write your own auth/credit logic
def verify_token(token):
    # Don't do this!
```

### 2. Config Over Code
```yaml
# ✅ GOOD: Put pricing in config.yaml
packages:
  - id: starter
    credits: 50
    price_usd: 4.99

# ❌ BAD: Hardcode pricing in Python
STARTER_PRICE = 4.99
```

### 3. Use Decorators
```python
# ✅ GOOD: Use decorators
@require_auth
@track_duration('api.generate')
def generate():
    pass

# ❌ BAD: Inline auth/tracking logic
def generate():
    token = get_token_from_header()
    user = verify_token(token)
    start = time.time()
    # ...
```

### 4. Handle Errors Gracefully
```python
from shared.credits.exceptions import InsufficientCreditsError

try:
    manager.deduct_credits(user_id, 100, "Generation")
except InsufficientCreditsError as e:
    return {'error': 'Insufficient credits', 'needed': e.required, 'have': e.available}, 402
```

---

## 📚 DOCUMENTATION

- [AUTH.md](docs/AUTH.md) - Complete auth documentation
- [CREDITS.md](docs/CREDITS.md) - Credit system guide
- [PAYMENTS.md](docs/PAYMENTS.md) - Payment integration
- [ANALYTICS.md](docs/ANALYTICS.md) - Analytics setup
- [TELEMETRY.md](docs/TELEMETRY.md) - Telemetry usage
- [LOGGING.md](docs/LOGGING.md) - Logging configuration
- [DATABASE.md](docs/DATABASE.md) - Database utilities
- [ADMIN.md](docs/ADMIN.md) - 🆕 Admin panel & config management
- [FRONTEND.md](docs/FRONTEND.md) - Frontend components
- [ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md) - Environment configuration

---

## 🤖 FOR AI ASSISTANTS

**IMPORTANT**: When working on applications derived from this template:

1. **ALWAYS** use the shared modules - never write duplicate functionality
2. **ALWAYS** put configuration in YAML files, not hardcoded in Python
3. **ALWAYS** use the provided decorators for auth and tracking
4. **NEVER** expose credentials or secrets in code
5. **FOLLOW** the established patterns for consistency

See [COPILOT_INSTRUCTIONS.md](COPILOT_INSTRUCTIONS.md) for detailed AI assistant guidelines.

---

*This template is your starting point. Modify and extend as needed, but always maintain the core patterns for consistency across applications.*
