# 🔐 Environment Setup Guide

This guide explains how to configure all environment variables required for applications built from this template.

---

## 📋 Required Environment Variables

### Supabase (Authentication + Database)

```bash
# Supabase Project URL
SUPABASE_URL=https://your-project-id.supabase.co

# Supabase Anonymous (Public) Key
# Used for client-side operations
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Supabase Service Role Key (KEEP SECRET!)
# Used for admin operations, bypasses RLS
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Supabase JWT Secret (for local token verification)
# Found in: Supabase Dashboard > Settings > API > JWT Secret
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase
```

### Stripe (Payments)

```bash
# Stripe Secret Key
# Found in: Stripe Dashboard > Developers > API Keys
STRIPE_SECRET_KEY=sk_test_...   # Use sk_live_... for production

# Stripe Webhook Secret
# Created when setting up webhook endpoint
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe Publishable Key (for frontend)
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### Analytics (Umami)

```bash
# Umami Website ID
# Found in: Umami Dashboard > Settings > Websites
UMAMI_WEBSITE_ID=your-website-id

# Umami API URL (default: cloud.umami.is)
UMAMI_API_URL=https://cloud.umami.is

# Umami API Key (optional, for server-side tracking)
UMAMI_API_KEY=your-api-key

# Enable/disable analytics
UMAMI_ENABLED=true
```

### Application Settings

```bash
# Application Environment
ENVIRONMENT=development  # development | staging | production

# API URL for frontend
VITE_API_URL=http://localhost:8000/api

# Debug mode
DEBUG=true  # Set to false in production

# Secret key for session management
SECRET_KEY=your-random-secret-key-here
```

---

## 📁 Environment File Template

Create a `.env` file in your application root:

```bash
# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================
# Copy this file to .env and fill in your values
# NEVER commit .env to version control!
# =============================================================================

# -----------------------------------------------------------------------------
# APPLICATION
# -----------------------------------------------------------------------------
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=change-this-to-a-random-string

# -----------------------------------------------------------------------------
# SUPABASE
# -----------------------------------------------------------------------------
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_JWT_SECRET=your-jwt-secret

# -----------------------------------------------------------------------------
# STRIPE
# -----------------------------------------------------------------------------
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# -----------------------------------------------------------------------------
# ANALYTICS (UMAMI)
# -----------------------------------------------------------------------------
UMAMI_WEBSITE_ID=your-website-id
UMAMI_API_URL=https://cloud.umami.is
UMAMI_ENABLED=true

# -----------------------------------------------------------------------------
# FRONTEND (VITE)
# -----------------------------------------------------------------------------
VITE_API_URL=http://localhost:8000/api
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
VITE_UMAMI_WEBSITE_ID=your-website-id
```

---

## 🔧 Getting Your Credentials

### Supabase Setup

1. **Create a Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project

2. **Get API Keys**
   - Navigate to: Settings > API
   - Copy:
     - Project URL → `SUPABASE_URL`
     - `anon` public key → `SUPABASE_KEY`
     - `service_role` key → `SUPABASE_SERVICE_KEY`
     - JWT Secret → `SUPABASE_JWT_SECRET`

3. **Set Up Database Tables**
   - Run the SQL scripts in `shared/database/` to create required tables
   - See [DATABASE.md](DATABASE.md) for details

### Stripe Setup

1. **Create a Stripe Account**
   - Go to [stripe.com](https://stripe.com)
   - Create an account

2. **Get API Keys**
   - Navigate to: Developers > API Keys
   - Copy:
     - Secret key → `STRIPE_SECRET_KEY`
     - Publishable key → `VITE_STRIPE_PUBLISHABLE_KEY`

3. **Set Up Webhooks**
   - Navigate to: Developers > Webhooks
   - Add endpoint: `https://your-app.com/api/stripe/webhook`
   - Select events:
     - `checkout.session.completed`
     - `payment_intent.succeeded`
     - `payment_intent.failed`
   - Copy Webhook Secret → `STRIPE_WEBHOOK_SECRET`

### Umami Setup

1. **Create Umami Account**
   - Go to [umami.is](https://umami.is) (or self-host)
   - Create an account

2. **Add Your Website**
   - Add a new website in Umami
   - Copy Website ID → `UMAMI_WEBSITE_ID`

---

## 🔒 Security Best Practices

### DO:
- ✅ Store `.env` files outside version control
- ✅ Use different credentials for development/staging/production
- ✅ Rotate keys periodically
- ✅ Use environment-specific `.env` files (`.env.development`, `.env.production`)
- ✅ Limit service key access to server-side code only

### DON'T:
- ❌ Commit `.env` files to git
- ❌ Share credentials in plain text
- ❌ Use production keys in development
- ❌ Expose service keys to frontend
- ❌ Log sensitive credentials

---

## 📊 Environment-Specific Configuration

### Development

```bash
ENVIRONMENT=development
DEBUG=true
STRIPE_SECRET_KEY=sk_test_...
SUPABASE_URL=https://dev-project.supabase.co
```

### Staging

```bash
ENVIRONMENT=staging
DEBUG=false
STRIPE_SECRET_KEY=sk_test_...
SUPABASE_URL=https://staging-project.supabase.co
```

### Production

```bash
ENVIRONMENT=production
DEBUG=false
STRIPE_SECRET_KEY=sk_live_...
SUPABASE_URL=https://prod-project.supabase.co
```

---

## 🧪 Verifying Your Setup

### Quick Verification Script

```python
#!/usr/bin/env python3
"""Verify environment configuration"""
import os

required_vars = [
    'SUPABASE_URL',
    'SUPABASE_KEY',
    'SUPABASE_SERVICE_KEY',
    'STRIPE_SECRET_KEY',
]

optional_vars = [
    'SUPABASE_JWT_SECRET',
    'STRIPE_WEBHOOK_SECRET',
    'UMAMI_WEBSITE_ID',
]

print("Checking required environment variables...\n")

missing = []
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {'*' * min(len(value), 10)}...")
    else:
        print(f"❌ {var}: MISSING")
        missing.append(var)

print("\nChecking optional environment variables...\n")

for var in optional_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {'*' * min(len(value), 10)}...")
    else:
        print(f"⚠️  {var}: Not set (optional)")

if missing:
    print(f"\n❌ Missing {len(missing)} required variables!")
    exit(1)
else:
    print("\n✅ All required variables are set!")
```

Run with:
```bash
python verify_env.py
```

---

## 🚀 Loading Environment Variables

### Python (with python-dotenv)

```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access variables
supabase_url = os.getenv('SUPABASE_URL')
```

### Frontend (Vite)

Vite automatically loads `.env` files. Variables must be prefixed with `VITE_`:

```typescript
// Access in code
const apiUrl = import.meta.env.VITE_API_URL;
const stripeKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;
```

---

## 📚 Related Documentation

- [AUTH.md](AUTH.md) - Supabase authentication setup
- [CREDITS.md](CREDITS.md) - Stripe payment integration
- [ANALYTICS.md](ANALYTICS.md) - Umami analytics setup
- [DATABASE.md](DATABASE.md) - Database schema and setup
