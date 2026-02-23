# 💳 Credits & Payments Module

The credits module provides a complete credit management system with Stripe integration.

---

## 📦 Module Structure

```
shared/credits/
├── __init__.py           # Factory functions and exports
├── base.py               # Abstract CreditManager interface
├── models.py             # Pydantic data models
├── exceptions.py         # Custom exceptions
├── config.yaml           # Pricing configuration
├── config_loader.py      # YAML config loader with caching
├── pricing_service.py    # Price calculations
├── stripe_service.py     # Stripe integration
└── providers/
    └── supabase.py       # Supabase implementation
```

---

## 🚀 Quick Start

### Check Balance and Deduct Credits

```python
from shared.credits import get_credit_manager
from shared.credits.exceptions import InsufficientCreditsError

manager = get_credit_manager()

# Get balance
balance = manager.get_balance(user_id)
print(f"User has {balance.credits} credits")

# Check and deduct
cost = 10
if manager.check_sufficient_credits(user_id, cost):
    transaction = manager.deduct_credits(
        user_id=user_id,
        amount=cost,
        description="Image generation",
        metadata={'model': 'flux-dev'}
    )
    print(f"Deducted {cost} credits. New balance: {transaction.balance_after}")
else:
    print("Insufficient credits!")
```

### Create Stripe Checkout

```python
from shared.credits import get_stripe_service

stripe_svc = get_stripe_service()

result = stripe_svc.create_package_checkout(
    user_id=user_id,
    user_email=user_email,
    package_id='creator',
    success_url='https://yourapp.com/success',
    cancel_url='https://yourapp.com/cancel'
)

# Redirect user to Stripe
redirect_url = result.checkout_url
```

---

## 📖 API Reference

### CreditManager

#### `get_balance(user_id: str) -> CreditBalance`
Get user's current credit balance.

```python
balance = manager.get_balance(user_id)
print(balance.credits)       # Current credits
print(balance.last_updated)  # Last update timestamp
```

#### `check_sufficient_credits(user_id: str, required: int) -> bool`
Check if user has enough credits.

```python
if manager.check_sufficient_credits(user_id, 100):
    # Proceed with operation
    pass
```

#### `deduct_credits(user_id, amount, description, metadata) -> CreditTransaction`
Deduct credits from user's balance.

```python
try:
    transaction = manager.deduct_credits(
        user_id=user_id,
        amount=10,
        description="Generated image",
        metadata={
            'model': 'flux-dev',
            'prompt': 'A beautiful sunset'
        }
    )
except InsufficientCreditsError as e:
    print(f"Need {e.required}, have {e.available}")
```

#### `add_credits(user_id, amount, transaction_type, description, metadata) -> CreditTransaction`
Add credits to user's balance.

```python
from shared.credits import TransactionType

transaction = manager.add_credits(
    user_id=user_id,
    amount=100,
    transaction_type=TransactionType.PURCHASE,
    description="Purchased Creator Pack",
    metadata={'package_id': 'creator', 'payment_id': 'pi_xxx'}
)
```

#### `get_transaction_history(user_id, page, page_size) -> TransactionHistory`
Get paginated transaction history.

```python
history = manager.get_transaction_history(user_id, page=1, page_size=20)
for txn in history.transactions:
    print(f"{txn.created_at}: {txn.amount} - {txn.description}")
```

---

## 💰 Pricing Configuration

### config.yaml Structure

```yaml
# Credit Packages (One-time purchases)
packages:
  - id: starter
    name: "Starter Pack"
    description: "Perfect for trying out"
    credits: 50
    price_usd: 4.99
    active: true
    popular: false
    
  - id: creator
    name: "Creator Pack"
    description: "Best value for creators"
    credits: 150
    price_usd: 9.99
    active: true
    popular: true
    badge: "Best Value"

# Subscriptions (Recurring)
subscriptions:
  - id: pro_monthly
    name: "Pro Monthly"
    credits_per_period: 500
    price_usd: 24.99
    interval: month
    trial_days: 7
    features:
      - "500 credits/month"
      - "Priority generation"

# Coupons
coupons:
  - code: WELCOME10
    type: percent
    discount: 10
    applies_to: all
    active: true

# Model Costs
models:
  flux-schnell:
    cost_per_generation: 5
  flux-dev:
    cost_per_generation: 10
  gpt-image-1:
    cost_per_generation: 8
```

### Accessing Pricing

```python
from shared.credits import get_pricing_service

pricing = get_pricing_service()

# Get all packages
packages = pricing.get_packages()

# Calculate price with coupon
price = pricing.calculate_package_price(
    package_id='creator',
    coupon_code='WELCOME10',
    is_first_purchase=True
)
print(f"Final price: ${price.final_price}")
print(f"Credits: {price.total_credits}")

# Get model cost
cost = pricing.get_model_cost('flux-dev')
```

---

## 💳 Stripe Integration

### Create Package Checkout

```python
from shared.credits import get_stripe_service

stripe_svc = get_stripe_service()

result = stripe_svc.create_package_checkout(
    user_id='user_123',
    user_email='user@example.com',
    package_id='creator',
    success_url='https://app.com/success?session_id={CHECKOUT_SESSION_ID}',
    cancel_url='https://app.com/cancel',
    coupon_code='WELCOME10',  # Optional
    is_first_purchase=True    # Optional, for bonus credits
)

if result.success:
    return {'checkout_url': result.checkout_url}
else:
    return {'error': result.error}
```

### Create Subscription Checkout

```python
result = stripe_svc.create_subscription_checkout(
    user_id='user_123',
    user_email='user@example.com',
    subscription_id='pro_monthly',
    success_url='https://app.com/success',
    cancel_url='https://app.com/cancel'
)
```

### Handle Webhooks

```python
@app.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    result = stripe_svc.handle_webhook(payload, sig_header)
    
    if result.success:
        # Credits already added by webhook handler
        return {'received': True}
    else:
        return {'error': result.error}, 400
```

---

## ⚠️ Exception Handling

### InsufficientCreditsError

```python
from shared.credits.exceptions import InsufficientCreditsError

try:
    manager.deduct_credits(user_id, 100, "Generation")
except InsufficientCreditsError as e:
    return {
        'error': 'Insufficient credits',
        'required': e.required,
        'available': e.available,
        'shortage': e.shortage
    }, 402
```

### InvalidTransactionError

```python
from shared.credits.exceptions import InvalidTransactionError

try:
    manager.deduct_credits(user_id, -10, "Invalid")  # Negative amount
except InvalidTransactionError as e:
    return {'error': str(e)}, 400
```

### ProviderError

```python
from shared.credits.exceptions import ProviderError

try:
    balance = manager.get_balance(user_id)
except ProviderError as e:
    logger.error(f"Database error: {e}")
    return {'error': 'Service unavailable'}, 503
```

---

## 🔄 Credit Flow Patterns

### Generation Flow

```python
@app.route('/api/generate', methods=['POST'])
@require_auth
def generate():
    user = get_current_user()
    data = request.json
    
    # Get cost from config
    model = data.get('model', 'flux-schnell')
    cost = pricing.get_model_cost(model)
    
    # Check credits BEFORE generation
    if not manager.check_sufficient_credits(user['id'], cost):
        balance = manager.get_balance(user['id'])
        return {
            'error': 'Insufficient credits',
            'required': cost,
            'available': balance.credits
        }, 402
    
    # Do the generation
    result = generate_image(data['prompt'], model)
    
    # Deduct credits AFTER success
    manager.deduct_credits(
        user_id=user['id'],
        amount=cost,
        description=f"Image generation ({model})",
        metadata={
            'model': model,
            'prompt_preview': data['prompt'][:100]
        }
    )
    
    return {'success': True, 'result': result}
```

### Purchase Flow

```
1. User selects package
2. Create Stripe checkout session
3. User completes payment on Stripe
4. Stripe sends webhook
5. Webhook handler adds credits
6. User sees updated balance
```

---

## 🗄️ Database Schema

Required Supabase tables:

```sql
-- User profiles with credits
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    credits INTEGER DEFAULT 0 CHECK (credits >= 0),
    subscription_tier TEXT DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transaction history
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    amount INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RPC function for atomic deduction
CREATE OR REPLACE FUNCTION deduct_user_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_description TEXT,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
    v_transaction_id UUID;
BEGIN
    -- Lock row and get current balance
    SELECT credits INTO v_current_balance
    FROM user_profiles
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Check sufficient credits
    IF v_current_balance < p_amount THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Insufficient credits',
            'current_balance', v_current_balance
        );
    END IF;
    
    -- Calculate new balance
    v_new_balance := v_current_balance - p_amount;
    
    -- Update balance
    UPDATE user_profiles
    SET credits = v_new_balance, updated_at = NOW()
    WHERE user_id = p_user_id;
    
    -- Record transaction
    INSERT INTO credit_transactions (
        user_id, amount, balance_before, balance_after,
        transaction_type, description, metadata
    ) VALUES (
        p_user_id, -p_amount, v_current_balance, v_new_balance,
        'deduction', p_description, p_metadata
    )
    RETURNING id INTO v_transaction_id;
    
    RETURN jsonb_build_object(
        'success', true,
        'transaction_id', v_transaction_id,
        'balance_before', v_current_balance,
        'balance_after', v_new_balance
    );
END;
$$;
```

---

## 📚 Related Documentation

- [PAYMENTS.md](PAYMENTS.md) - Payment tracking
- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - Stripe configuration
- [DATABASE.md](DATABASE.md) - Database setup
