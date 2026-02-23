-- Fix ambiguous created_at references in RPC functions
-- Run this to fix the ambiguous column error

DROP FUNCTION IF EXISTS deduct_user_credits(UUID, INTEGER, TEXT, JSONB);
DROP FUNCTION IF EXISTS add_user_credits(UUID, INTEGER, TEXT, TEXT, JSONB);

-- Recreate deduct_user_credits with qualified column names
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


-- Recreate add_user_credits with qualified column names
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

-- Grant permissions
GRANT EXECUTE ON FUNCTION deduct_user_credits TO authenticated;
GRANT EXECUTE ON FUNCTION add_user_credits TO authenticated;
