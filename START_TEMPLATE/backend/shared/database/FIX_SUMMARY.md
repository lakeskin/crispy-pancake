# Created_At Ambiguity Fix - Summary

## Problem
PostgreSQL was returning: **"column reference created_at is ambiguous"**

## Root Cause
In multiple RPC functions (deduct_user_credits, add_user_credits, adjust_user_balance, refund_user_transaction), we had:

```sql
DECLARE
    v_created_at TIMESTAMPTZ;  -- Variable declaration
...
INSERT INTO credit_transactions (..., created_at)  -- Column in INSERT
VALUES (..., NOW())
RETURNING id, created_at INTO v_transaction_id, v_created_at;  -- AMBIGUOUS!
```

PostgreSQL couldn't tell if `created_at` in the RETURNING clause referred to:
1. The table column `credit_transactions.created_at`
2. The declared variable `v_created_at`

## Solution
Changed all RETURNING clauses to qualify the column names:

**BEFORE:**
```sql
RETURNING id, created_at INTO v_transaction_id, v_created_at;
```

**AFTER:**
```sql
RETURNING credit_transactions.id, credit_transactions.created_at INTO v_transaction_id, v_created_at;
```

Also removed `created_at` from INSERT since it has a DEFAULT NOW() anyway:

**BEFORE:**
```sql
INSERT INTO credit_transactions (
    user_id, amount, ..., created_at
) VALUES (
    p_user_id, p_amount, ..., NOW()
)
```

**AFTER:**
```sql
INSERT INTO credit_transactions (
    user_id, amount, ...
) VALUES (
    p_user_id, p_amount, ...
)
```

## Fixed Functions
✅ deduct_user_credits()
✅ add_user_credits()
✅ adjust_user_balance()
✅ refund_user_transaction()

## Next Steps
1. ✅ SQL regenerated and copied to clipboard (19,690 chars, 658 lines)
2. ⏳ Paste in Supabase SQL Editor: https://supabase.com/dashboard/project/fjbfqrbjbgjqnxiespcy/sql/new
3. ⏳ Click Run
4. ⏳ Run tests: `python run_tests_debug.py`
5. 🎯 Expected: Credits tests should pass (currently 1/9, aiming for 9/9)
