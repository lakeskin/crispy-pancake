# Payment Tracking System

A reusable, database-backed payment tracking module designed for adaptability, reusability, and easy integration.

## Features

- ✅ **Full Payment Lifecycle Tracking**: Track payments from checkout creation through completion, failure, or refund
- ✅ **Duplicate Prevention**: Prevent double-crediting with session-based duplicate detection
- ✅ **Provider Agnostic**: Works with any payment provider (Stripe, PayPal, etc.)
- ✅ **Database Agnostic**: Implement `PaymentStore` for any backend (Supabase, Firebase, PostgreSQL)
- ✅ **Recovery Mechanism**: Built-in support for webhook failure recovery
- ✅ **Audit Trail**: Complete history of all payment attempts and status changes
- ✅ **Configurable**: All settings can be customized via `config.yaml`

## Architecture

```
shared/payments/
├── __init__.py           # Main exports and factory functions
├── tracker.py            # PaymentTracker service and data models
├── base.py               # Abstract PaymentProvider interface
├── models.py             # Pydantic models for payments
├── exceptions.py         # Custom exceptions
├── config.yaml           # Configuration settings
└── stores/
    ├── __init__.py
    └── supabase.py       # Supabase implementation
```

## Quick Start

### 1. Run the Migration

First, run the migration to update your `payment_transactions` table:

```sql
-- Run in Supabase SQL Editor
\i database/migrations/002_payment_tracking.sql
```

### 2. Use the Payment Tracker

```python
from shared.payments import get_payment_tracker

# Get a configured tracker
tracker = get_payment_tracker(
    store_type='supabase',
    supabase_client=your_supabase_client,
    session_expiry_minutes=30
)

# Create a pending payment BEFORE redirecting to Stripe
payment = tracker.create_pending_payment(
    user_id='user_123',
    amount_cents=999,
    credits_to_add=150,
    provider='stripe',
    session_id='cs_xxx',  # From Stripe checkout session
    package_id='creator',
    package_name='Creator Pack'
)

# After webhook confirms payment (or via verify-payment endpoint)
tracker.mark_completed(payment.id)
tracker.mark_credits_added(payment.id)

# Check for duplicates before adding credits
if tracker.is_duplicate(session_id):
    print("Already processed!")
```

## Payment Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PAYMENT FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. User clicks "Buy Credits"                                               │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  /checkout/package                                                   │    │
│  │  - Creates Stripe checkout session                                   │    │
│  │  - Creates PENDING payment record in database                        │    │
│  │  - Returns checkout URL                                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Stripe Checkout                                                     │    │
│  │  - User enters payment details                                       │    │
│  │  - Payment processed by Stripe                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│         │                                                                   │
│         ├──────────────────┬──────────────────┐                             │
│         │                  │                  │                             │
│    (Webhook)         (Success Page)    (Webhook Failed)                     │
│         │                  │                  │                             │
│         ▼                  ▼                  ▼                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                       │
│  │ /webhook     │  │ CreditsSuccess│  │ /verify-     │                       │
│  │              │  │ (frontend)   │  │  payment     │                       │
│  │ - Verify sig │  │              │  │              │                       │
│  │ - Check dup  │  │ - Shows      │  │ - Verify w/  │                       │
│  │ - Add credits│  │   success    │  │   Stripe API │                       │
│  │ - Mark done  │  │ - Auto-verify│  │ - Check dup  │                       │
│  └──────────────┘  │   if needed  │  │ - Add credits│                       │
│         │          └──────┬───────┘  │ - Mark done  │                       │
│         │                 │          └──────────────┘                       │
│         └────────────┬────┴────────────────┘                                │
│                      │                                                      │
│                      ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Database: payment_transactions                                     │    │
│  │  - status: 'completed'                                              │    │
│  │  - credits_added: true                                              │    │
│  │  - credits_added_at: timestamp                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Payment Record Status

| Status | Description |
|--------|-------------|
| `pending` | Checkout created, awaiting user payment |
| `processing` | Payment in progress (webhook received) |
| `completed` | Payment successful |
| `failed` | Payment failed |
| `expired` | Checkout session expired |
| `cancelled` | User cancelled |
| `refunded` | Full refund processed |
| `partially_refunded` | Partial refund processed |

## API Endpoints

### Checkout

```
POST /api/credits/checkout/package
{
    "package_id": "creator",
    "coupon_code": "WELCOME10"  // optional
}
→ { checkout_url, session_id, payment_id }
```

### Webhook

```
POST /api/credits/webhook
(Stripe signature verified)
→ { status: "success" }
```

### Verify Payment (Recovery)

```
POST /api/credits/verify-payment
{
    "session_id": "cs_test_xxx"
}
→ { success, payment_verified, credits_added, new_balance }
```

### Payment History

```
GET /api/credits/payment-history?page=1&page_size=20&status=completed
→ { payments: [...], total_count, page, page_size, has_more }
```

### Payment Stats

```
GET /api/credits/payment-stats
→ { total_spent_usd, total_credits_purchased, completed_payments, ... }
```

## Database Schema

The `payment_transactions` table tracks all payment attempts:

```sql
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(id),
    
    -- Amount info
    amount_cents INTEGER NOT NULL,
    amount_usd DECIMAL(10, 2),
    credits_to_add INTEGER NOT NULL,
    
    -- Status
    status TEXT NOT NULL,  -- pending, processing, completed, failed, etc.
    
    -- Provider info
    provider TEXT NOT NULL,  -- 'stripe', 'paypal', etc.
    provider_session_id TEXT,  -- Checkout session ID
    provider_payment_id TEXT,  -- Payment intent ID
    
    -- Package info
    package_id TEXT,
    package_name TEXT,
    
    -- Credit tracking
    credits_added BOOLEAN DEFAULT FALSE,
    credits_added_at TIMESTAMP,
    credit_transaction_id UUID,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- Error tracking
    error_message TEXT,
    error_code TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'
);
```

## Adding a New Database Backend

Implement the `PaymentStore` interface:

```python
from shared.payments.tracker import PaymentStore, PaymentRecord

class MyDatabasePaymentStore(PaymentStore):
    def create(self, payment: PaymentRecord) -> PaymentRecord:
        # Insert into your database
        pass
    
    def get_by_id(self, payment_id: str) -> Optional[PaymentRecord]:
        # Query by internal ID
        pass
    
    def get_by_session_id(self, session_id: str) -> Optional[PaymentRecord]:
        # Query by provider session ID
        pass
    
    def update(self, payment: PaymentRecord) -> PaymentRecord:
        # Update existing record
        pass
    
    # ... implement other required methods
```

Then register it:

```python
def get_payment_tracker(store_type='my_database', ...):
    if store_type == 'my_database':
        store = MyDatabasePaymentStore(...)
        return PaymentTracker(store)
```

## Configuration

See `shared/payments/config.yaml` for all configurable settings:

```yaml
payment_tracking:
  session_expiry_minutes: 30
  check_duplicates_before_credit: true
  
recovery:
  enabled: true
  auto_verify_on_success_page: true
  max_verification_attempts: 3
```

## Integration with New Projects

1. Copy `shared/payments/` to your project
2. Run the database migration
3. Configure `config.yaml`
4. Use `get_payment_tracker()` in your routes

The module is designed to be completely self-contained and portable.
