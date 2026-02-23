-- ============================================================================
-- CREDIT SYSTEM DATABASE MIGRATION
-- ============================================================================
-- This migration creates the necessary tables, RPC functions, and triggers
-- for the credit management system.
--
-- Requirements:
-- - user_profiles table must exist with user_id column
-- - UUID extension must be enabled
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLES
-- ============================================================================

-- Add credits column to user_profiles if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_profiles' 
        AND column_name = 'credits'
    ) THEN
        ALTER TABLE user_profiles 
        ADD COLUMN credits INTEGER DEFAULT 0 CHECK (credits >= 0);
    END IF;
END $$;

-- Create credit_transactions table
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,  -- Positive for additions, negative for deductions
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
    transaction_type TEXT NOT NULL,  -- 'deduction', 'purchase', 'signup_bonus', etc.
    description TEXT NOT NULL DEFAULT '',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id 
    ON credit_transactions(user_id);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at 
    ON credit_transactions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_type 
    ON credit_transactions(transaction_type);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_created 
    ON credit_transactions(user_id, created_at DESC);

-- ============================================================================
-- RPC FUNCTIONS
-- ============================================================================

-- Function: deduct_user_credits
-- Atomically deducts credits from user and records transaction
CREATE OR REPLACE FUNCTION deduct_user_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_description TEXT DEFAULT 'Credit deduction',
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
    success BOOLEAN,
    transaction_id UUID,
    balance_before INTEGER,
    balance_after INTEGER,
    error TEXT,
    current_balance INTEGER,
    created_at TIMESTAMPTZ
) AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
    v_transaction_id UUID;
    v_created_at TIMESTAMPTZ;
BEGIN
    -- Validate amount
    IF p_amount <= 0 THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            0,
            0,
            'Amount must be positive'::TEXT,
            0,
            NOW();
        RETURN;
    END IF;
    
    -- Get current balance with row lock
    SELECT credits INTO v_current_balance
    FROM user_profiles
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Check if user exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            0,
            0,
            'User not found'::TEXT,
            0,
            NOW();
        RETURN;
    END IF;
    
    -- Check sufficient credits
    IF v_current_balance < p_amount THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            v_current_balance,
            v_current_balance,
            format('Insufficient credits. Required: %s, Available: %s', p_amount, v_current_balance)::TEXT,
            v_current_balance,
            NOW();
        RETURN;
    END IF;
    
    -- Calculate new balance
    v_new_balance := v_current_balance - p_amount;
    
    -- Update user balance
    UPDATE user_profiles
    SET credits = v_new_balance,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    -- Record transaction
    INSERT INTO credit_transactions (
        user_id,
        amount,
        balance_before,
        balance_after,
        transaction_type,
        description,
        metadata
    ) VALUES (
        p_user_id,
        -p_amount,  -- Negative for deduction
        v_current_balance,
        v_new_balance,
        'deduction',
        p_description,
        p_metadata
    )
    RETURNING credit_transactions.id, credit_transactions.created_at INTO v_transaction_id, v_created_at;
    
    -- Return success
    RETURN QUERY SELECT 
        true,
        v_transaction_id,
        v_current_balance,
        v_new_balance,
        NULL::TEXT,
        v_new_balance,
        v_created_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Function: add_user_credits
-- Atomically adds credits to user and records transaction
CREATE OR REPLACE FUNCTION add_user_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_transaction_type TEXT,
    p_description TEXT DEFAULT 'Credit addition',
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
    success BOOLEAN,
    transaction_id UUID,
    balance_before INTEGER,
    balance_after INTEGER,
    error TEXT,
    created_at TIMESTAMPTZ
) AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
    v_transaction_id UUID;
    v_created_at TIMESTAMPTZ;
BEGIN
    -- Validate amount
    IF p_amount <= 0 THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            0,
            0,
            'Amount must be positive'::TEXT,
            NOW();
        RETURN;
    END IF;
    
    -- Get current balance with row lock
    SELECT credits INTO v_current_balance
    FROM user_profiles
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Check if user exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            0,
            0,
            'User not found'::TEXT,
            NOW();
        RETURN;
    END IF;
    
    -- Calculate new balance
    v_new_balance := v_current_balance + p_amount;
    
    -- Update user balance
    UPDATE user_profiles
    SET credits = v_new_balance,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    -- Record transaction
    INSERT INTO credit_transactions (
        user_id,
        amount,
        balance_before,
        balance_after,
        transaction_type,
        description,
        metadata
    ) VALUES (
        p_user_id,
        p_amount,  -- Positive for addition
        v_current_balance,
        v_new_balance,
        p_transaction_type,
        p_description,
        p_metadata
    )
    RETURNING credit_transactions.id, credit_transactions.created_at INTO v_transaction_id, v_created_at;
    
    -- Return success
    RETURN QUERY SELECT 
        true,
        v_transaction_id,
        v_current_balance,
        v_new_balance,
        NULL::TEXT,
        v_created_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Function: adjust_user_balance
-- Admin function to adjust user balance (positive or negative)
CREATE OR REPLACE FUNCTION adjust_user_balance(
    p_user_id UUID,
    p_amount INTEGER,
    p_reason TEXT,
    p_admin_id TEXT,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
    success BOOLEAN,
    transaction_id UUID,
    balance_before INTEGER,
    balance_after INTEGER,
    error TEXT,
    created_at TIMESTAMPTZ
) AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
    v_transaction_id UUID;
    v_created_at TIMESTAMPTZ;
    v_metadata JSONB;
BEGIN
    -- Add admin_id to metadata
    v_metadata := p_metadata || jsonb_build_object('admin_id', p_admin_id);
    
    -- Get current balance with row lock
    SELECT credits INTO v_current_balance
    FROM user_profiles
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Check if user exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            0,
            0,
            'User not found'::TEXT,
            NOW();
        RETURN;
    END IF;
    
    -- Calculate new balance
    v_new_balance := v_current_balance + p_amount;
    
    -- Check that new balance won't be negative
    IF v_new_balance < 0 THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            v_current_balance,
            v_current_balance,
            format('Adjustment would result in negative balance: %s', v_new_balance)::TEXT,
            NOW();
        RETURN;
    END IF;
    
    -- Update user balance
    UPDATE user_profiles
    SET credits = v_new_balance,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    -- Record transaction
    INSERT INTO credit_transactions (
        user_id,
        amount,
        balance_before,
        balance_after,
        transaction_type,
        description,
        metadata
    ) VALUES (
        p_user_id,
        p_amount,
        v_current_balance,
        v_new_balance,
        'admin_adjustment',
        format('Admin adjustment: %s', p_reason),
        v_metadata
    )
    RETURNING credit_transactions.id, credit_transactions.created_at INTO v_transaction_id, v_created_at;
    
    -- Return success
    RETURN QUERY SELECT 
        true,
        v_transaction_id,
        v_current_balance,
        v_new_balance,
        NULL::TEXT,
        v_created_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Function: refund_user_transaction
-- Refunds a previous transaction
CREATE OR REPLACE FUNCTION refund_user_transaction(
    p_user_id UUID,
    p_transaction_id UUID,
    p_amount INTEGER,
    p_reason TEXT
)
RETURNS TABLE (
    success BOOLEAN,
    transaction_id UUID,
    balance_before INTEGER,
    balance_after INTEGER,
    error TEXT,
    created_at TIMESTAMPTZ
) AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
    v_transaction_id UUID;
    v_created_at TIMESTAMPTZ;
    v_original_exists BOOLEAN;
BEGIN
    -- Validate amount
    IF p_amount <= 0 THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            0,
            0,
            'Amount must be positive'::TEXT,
            NOW();
        RETURN;
    END IF;
    
    -- Check if original transaction exists
    SELECT EXISTS(
        SELECT 1 FROM credit_transactions 
        WHERE id = p_transaction_id AND user_id = p_user_id
    ) INTO v_original_exists;
    
    IF NOT v_original_exists THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            0,
            0,
            'Original transaction not found'::TEXT,
            NOW();
        RETURN;
    END IF;
    
    -- Get current balance with row lock
    SELECT credits INTO v_current_balance
    FROM user_profiles
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Check if user exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT 
            false,
            NULL::UUID,
            0,
            0,
            'User not found'::TEXT,
            NOW();
        RETURN;
    END IF;
    
    -- Calculate new balance
    v_new_balance := v_current_balance + p_amount;
    
    -- Update user balance
    UPDATE user_profiles
    SET credits = v_new_balance,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    -- Record refund transaction
    INSERT INTO credit_transactions (
        user_id,
        amount,
        balance_before,
        balance_after,
        transaction_type,
        description,
        metadata
    ) VALUES (
        p_user_id,
        p_amount,
        v_current_balance,
        v_new_balance,
        'refund',
        format('Refund: %s', p_reason),
        jsonb_build_object('original_transaction_id', p_transaction_id)
    )
    RETURNING credit_transactions.id, credit_transactions.created_at INTO v_transaction_id, v_created_at;
    
    -- Return success
    RETURN QUERY SELECT 
        true,
        v_transaction_id,
        v_current_balance,
        v_new_balance,
        NULL::TEXT,
        v_created_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on credit_transactions
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;

-- Users can only view their own transactions
CREATE POLICY "Users can view own credit transactions"
    ON credit_transactions
    FOR SELECT
    USING (auth.uid() = user_id);

-- Only service role can insert transactions (via RPC functions)
CREATE POLICY "Only service role can insert transactions"
    ON credit_transactions
    FOR INSERT
    WITH CHECK (false);  -- Direct inserts blocked, use RPC functions

-- No updates or deletes allowed (append-only)
CREATE POLICY "No updates to transactions"
    ON credit_transactions
    FOR UPDATE
    USING (false);

CREATE POLICY "No deletes from transactions"
    ON credit_transactions
    FOR DELETE
    USING (false);


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get user's transaction summary
CREATE OR REPLACE FUNCTION get_user_credit_summary(p_user_id UUID)
RETURNS TABLE (
    current_balance INTEGER,
    total_spent INTEGER,
    total_earned INTEGER,
    transaction_count INTEGER,
    last_transaction_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        up.credits,
        COALESCE(SUM(CASE WHEN ct.amount < 0 THEN ABS(ct.amount) ELSE 0 END), 0)::INTEGER,
        COALESCE(SUM(CASE WHEN ct.amount > 0 THEN ct.amount ELSE 0 END), 0)::INTEGER,
        COUNT(ct.id)::INTEGER,
        MAX(ct.created_at)
    FROM user_profiles up
    LEFT JOIN credit_transactions ct ON ct.user_id = up.user_id
    WHERE up.user_id = p_user_id
    GROUP BY up.credits;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's current balance (simple query)
CREATE OR REPLACE FUNCTION get_user_balance(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
    v_balance INTEGER;
BEGIN
    SELECT COALESCE(credits, 0) INTO v_balance
    FROM user_profiles
    WHERE user_id = p_user_id;
    
    -- If user not found, return 0
    IF NOT FOUND THEN
        v_balance := 0;
    END IF;
    
    RETURN v_balance;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant execute permissions on RPC functions
GRANT EXECUTE ON FUNCTION deduct_user_credits TO authenticated;
GRANT EXECUTE ON FUNCTION add_user_credits TO authenticated;
GRANT EXECUTE ON FUNCTION adjust_user_balance TO authenticated;
GRANT EXECUTE ON FUNCTION refund_user_transaction TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_credit_summary TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_balance TO authenticated;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables exist
DO $$
BEGIN
    ASSERT (SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'credit_transactions')),
        'credit_transactions table not created';
    
    ASSERT (SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'credits')),
        'credits column not added to user_profiles';
    
    RAISE NOTICE 'Credit system migration completed successfully!';
END $$;
