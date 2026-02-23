# 💰 Payments Module

Payment tracking and lifecycle management.

---

## 📦 Module Structure

```
shared/payments/
├── __init__.py      # Public exports
├── base.py          # Abstract PaymentProvider interface
├── models.py        # Payment data models
├── tracker.py       # Payment tracking service
├── exceptions.py    # Custom exceptions
├── stores/          # Database implementations
└── config.yaml      # Payment configuration
```

---

## 🚀 Quick Start

```python
from shared.payments import get_payment_tracker

tracker = get_payment_tracker()

# Create pending payment
payment = tracker.create_pending_payment(
    user_id='user_123',
    amount_cents=999,
    credits_to_add=150,
    package_id='creator',
    provider='stripe'
)

# Update on success
tracker.complete_payment(
    payment_id=payment.id,
    provider_payment_id='pi_xxx'
)
```

---

## 📋 Payment Lifecycle

```
PENDING → PROCESSING → COMPLETED
                    ↘ FAILED
                    ↘ EXPIRED
                    ↘ CANCELLED

COMPLETED → REFUNDED
          → PARTIALLY_REFUNDED
```

### Status Definitions

| Status | Description |
|--------|-------------|
| `PENDING` | Checkout created, awaiting payment |
| `PROCESSING` | Payment in progress |
| `COMPLETED` | Payment successful |
| `FAILED` | Payment failed |
| `EXPIRED` | Checkout session expired |
| `CANCELLED` | User cancelled |
| `REFUNDED` | Full refund processed |
| `PARTIALLY_REFUNDED` | Partial refund |

---

## 📖 API Reference

### PaymentTracker

#### `create_pending_payment(...) -> PaymentRecord`

Create a new pending payment before Stripe checkout.

```python
payment = tracker.create_pending_payment(
    user_id='user_123',
    amount_cents=999,
    credits_to_add=150,
    package_id='creator',
    package_name='Creator Pack',
    provider='stripe',
    coupon_code='WELCOME10',
    discount_cents=100,
    original_amount_cents=1099,
    expires_at=datetime.utcnow() + timedelta(hours=1)
)
```

#### `update_status(payment_id, status, **kwargs)`

Update payment status.

```python
tracker.update_status(
    payment_id=payment.id,
    status=PaymentRecordStatus.PROCESSING,
    provider_payment_id='pi_xxx'
)
```

#### `complete_payment(payment_id, provider_payment_id)`

Mark payment as completed.

```python
tracker.complete_payment(
    payment_id=payment.id,
    provider_payment_id='pi_xxx'
)
```

#### `mark_credits_added(payment_id, transaction_id)`

Record that credits were added.

```python
tracker.mark_credits_added(
    payment_id=payment.id,
    transaction_id='txn_xxx'
)
```

#### `get_payment_by_session(session_id) -> PaymentRecord`

Find payment by Stripe session ID.

```python
payment = tracker.get_payment_by_session('cs_xxx')
```

---

## 🔄 Payment Flow Integration

### Complete Stripe Webhook Handler

```python
from flask import Flask, request
from shared.payments import get_payment_tracker, PaymentRecordStatus
from shared.credits import get_credit_manager

app = Flask(__name__)
tracker = get_payment_tracker()
credit_manager = get_credit_manager()

@app.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except Exception as e:
        return {'error': str(e)}, 400
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Find payment record
        payment = tracker.get_payment_by_session(session['id'])
        if not payment:
            return {'error': 'Payment not found'}, 404
        
        # Check for duplicates
        if payment.credits_added:
            return {'received': True, 'note': 'Already processed'}
        
        # Update status
        tracker.complete_payment(
            payment_id=payment.id,
            provider_payment_id=session.get('payment_intent')
        )
        
        # Add credits
        transaction = credit_manager.add_credits(
            user_id=payment.user_id,
            amount=payment.credits_to_add,
            transaction_type='purchase',
            description=f"Purchased {payment.package_name}",
            metadata={'payment_id': payment.id}
        )
        
        # Mark credits added
        tracker.mark_credits_added(
            payment_id=payment.id,
            transaction_id=transaction.id
        )
        
        return {'received': True}
    
    return {'received': True}
```

---

## 🛡️ Duplicate Prevention

The tracker prevents duplicate credit additions:

```python
# In PaymentRecord
@property
def can_add_credits(self) -> bool:
    """Check if credits can be added for this payment"""
    return self.is_completed and not self.credits_added

# Usage
payment = tracker.get_payment_by_session(session_id)

if not payment.can_add_credits:
    logger.warning("Credits already added", payment_id=payment.id)
    return

# Safe to add credits
```

---

## 📊 Data Model

### PaymentRecord

```python
@dataclass
class PaymentRecord:
    id: str
    user_id: str
    amount_cents: int
    amount_usd: float
    credits_to_add: int
    status: PaymentRecordStatus
    
    # Provider info
    provider: str
    provider_session_id: str
    provider_payment_id: str
    
    # Package info
    package_id: str
    package_name: str
    
    # Discount info
    coupon_code: str
    discount_cents: int
    original_amount_cents: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: datetime
    expires_at: datetime
    
    # Credits tracking
    credits_added: bool
    credits_added_at: datetime
    credit_transaction_id: str
    
    # Refund tracking
    refund_amount_cents: int
    refund_reason: str
    refunded_at: datetime
    
    # Error tracking
    error_message: str
    error_code: str
    retry_count: int
```

---

## ⚠️ Exceptions

```python
from shared.payments.exceptions import (
    PaymentError,
    InvalidCouponError,
    WebhookVerificationError
)

try:
    process_payment(...)
except InvalidCouponError as e:
    return {'error': 'Invalid coupon'}, 400
except WebhookVerificationError as e:
    return {'error': 'Invalid signature'}, 400
except PaymentError as e:
    logger.error("Payment error", error=str(e))
    return {'error': 'Payment failed'}, 500
```

---

## 📚 Related Documentation

- [CREDITS.md](CREDITS.md) - Credit management and Stripe integration
- [DATABASE.md](DATABASE.md) - Database schema
