# 🗄️ Database Module

Database utilities for Supabase.

---

## 📦 Module Structure

```
shared/database/
├── __init__.py          # Public exports
├── manager.py           # DatabaseManager class
├── storage.py           # Storage utilities
├── storage_manager.py   # Storage bucket management
├── setup_sql.py         # SQL setup utilities
└── sql/                 # SQL migration files
```

---

## 🚀 Quick Start

```python
from shared.database import DatabaseManager

# Get manager with Supabase client
manager = DatabaseManager(supabase_client)

# Check if table exists
if manager.table_exists('user_profiles'):
    print("Table exists")

# Get columns
columns = manager.get_table_columns('user_profiles')
```

---

## 📋 Required Tables

Your application needs these tables:

### user_profiles

```sql
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    username TEXT UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    credits INTEGER DEFAULT 0 CHECK (credits >= 0),
    subscription_tier TEXT DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id);
```

### credit_transactions

```sql
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

-- Index for user queries
CREATE INDEX idx_credit_transactions_user 
    ON credit_transactions(user_id, created_at DESC);
```

### payment_transactions

```sql
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    amount_cents INTEGER NOT NULL,
    credits_to_add INTEGER NOT NULL,
    status TEXT NOT NULL,
    provider TEXT DEFAULT 'stripe',
    provider_session_id TEXT,
    provider_payment_id TEXT,
    package_id TEXT,
    package_name TEXT,
    coupon_code TEXT,
    discount_cents INTEGER DEFAULT 0,
    credits_added BOOLEAN DEFAULT FALSE,
    credit_transaction_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
);
```

---

## 🔧 RPC Functions

### deduct_user_credits

```sql
CREATE OR REPLACE FUNCTION deduct_user_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_description TEXT DEFAULT '',
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
    -- Lock and get current balance
    SELECT credits INTO v_current_balance
    FROM user_profiles
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    IF v_current_balance IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'User not found'
        );
    END IF;
    
    IF v_current_balance < p_amount THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Insufficient credits',
            'current_balance', v_current_balance
        );
    END IF;
    
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

### add_user_credits

```sql
CREATE OR REPLACE FUNCTION add_user_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_transaction_type TEXT,
    p_description TEXT DEFAULT '',
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
    -- Lock and get current balance
    SELECT credits INTO v_current_balance
    FROM user_profiles
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    IF v_current_balance IS NULL THEN
        -- Create profile if doesn't exist
        INSERT INTO user_profiles (user_id, credits)
        VALUES (p_user_id, 0)
        ON CONFLICT (user_id) DO NOTHING;
        
        v_current_balance := 0;
    END IF;
    
    v_new_balance := v_current_balance + p_amount;
    
    -- Update balance
    UPDATE user_profiles
    SET credits = v_new_balance, updated_at = NOW()
    WHERE user_id = p_user_id;
    
    -- Record transaction
    INSERT INTO credit_transactions (
        user_id, amount, balance_before, balance_after,
        transaction_type, description, metadata
    ) VALUES (
        p_user_id, p_amount, v_current_balance, v_new_balance,
        p_transaction_type, p_description, p_metadata
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

### get_user_balance

```sql
CREATE OR REPLACE FUNCTION get_user_balance(p_user_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_balance INTEGER;
BEGIN
    SELECT credits INTO v_balance
    FROM user_profiles
    WHERE user_id = p_user_id;
    
    RETURN COALESCE(v_balance, 0);
END;
$$;
```

---

## 📖 API Reference

### DatabaseManager

```python
from shared.database import DatabaseManager

manager = DatabaseManager(supabase_client)

# Check table existence
exists = manager.table_exists('user_profiles')

# Get columns
columns = manager.get_table_columns('user_profiles')

# Get SQL for table creation
sql = manager.create_user_profiles_table()
```

### StorageManager

```python
from shared.database import StorageManager

storage = StorageManager(supabase_client)

# Create bucket
storage.create_bucket('images', public=True)

# Upload file
url = storage.upload_file('images', 'path/file.png', file_data)

# Get public URL
url = storage.get_public_url('images', 'path/file.png')

# Delete file
storage.delete_file('images', 'path/file.png')
```

---

## 🔒 Row Level Security

Always enable RLS on your tables:

```sql
-- Enable RLS
ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;

-- User can only see own data
CREATE POLICY "Users can view own data"
    ON your_table
    FOR SELECT
    USING (auth.uid() = user_id);

-- Service role bypasses RLS
-- Use SUPABASE_SERVICE_KEY for admin operations
```

---

## 📚 Related Documentation

- [CREDITS.md](CREDITS.md) - Credit system
- [AUTH.md](AUTH.md) - Authentication
- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - Supabase configuration
