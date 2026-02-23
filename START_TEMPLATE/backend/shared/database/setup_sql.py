#!/usr/bin/env python3
"""
Generate consolidated SQL for Supabase setup.
Copies to clipboard and provides direct link.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pyperclip

def main():
    print("=" * 80)
    print("SUPABASE SQL GENERATOR")
    print("=" * 80)
    
    # Load environment
    env_file = Path(__file__).parent.parent.parent / "applications" / "asaad_000_MultiImageGenerator" / ".env"
    
    if not env_file.exists():
        print(f"✗ Environment file not found: {env_file}")
        sys.exit(1)
    
    load_dotenv(env_file)
    
    url = os.getenv('SUPABASE_URL')
    if not url:
        print("✗ SUPABASE_URL not found in .env")
        sys.exit(1)
    
    project_ref = url.split('//')[1].split('.')[0]
    
    # Read migration SQL
    migration_file = Path(__file__).parent.parent / "credits" / "migration.sql"
    
    if not migration_file.exists():
        print(f"✗ Migration file not found: {migration_file}")
        sys.exit(1)
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Build complete SQL
    user_profiles_fix = """-- ============================================================================
-- FIX USER_PROFILES TABLE
-- ============================================================================

-- Add missing columns
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS email TEXT;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- Update existing rows to link user_id (if you have existing data)
-- UPDATE user_profiles SET user_id = id WHERE user_id IS NULL;

-- ============================================================================
-- DROP EXISTING POLICIES (if any)
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own credit transactions" ON credit_transactions;
DROP POLICY IF EXISTS "Service role can manage credit transactions" ON credit_transactions;
DROP POLICY IF EXISTS "Only service role can insert transactions" ON credit_transactions;
DROP POLICY IF EXISTS "No updates to transactions" ON credit_transactions;
DROP POLICY IF EXISTS "No deletes from transactions" ON credit_transactions;
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Service role can manage profiles" ON user_profiles;
DROP POLICY IF EXISTS "Service role can insert profiles" ON user_profiles;

-- ============================================================================
-- DROP EXISTING FUNCTIONS (if any)
-- ============================================================================

DROP FUNCTION IF EXISTS add_user_credits(UUID, INTEGER, TEXT, TEXT, JSONB);
DROP FUNCTION IF EXISTS deduct_user_credits(UUID, INTEGER, TEXT, JSONB);
DROP FUNCTION IF EXISTS adjust_user_balance(UUID, INTEGER, TEXT, TEXT, JSONB);
DROP FUNCTION IF EXISTS refund_user_transaction(UUID, UUID, INTEGER, TEXT);
DROP FUNCTION IF EXISTS get_user_credit_summary(UUID);
DROP FUNCTION IF EXISTS get_user_credits(UUID);
DROP FUNCTION IF EXISTS get_credit_balance(UUID);
DROP FUNCTION IF EXISTS record_credit_transaction(UUID, TEXT, INTEGER, TEXT, JSONB);

-- ============================================================================
-- DROP AND RECREATE CREDIT_TRANSACTIONS TABLE
-- ============================================================================

-- Drop the table completely to ensure clean schema
DROP TABLE IF EXISTS credit_transactions CASCADE;

"""
    
    storage_buckets = """
-- ============================================================================
-- CREATE STORAGE BUCKETS (Run this first, then create buckets in Storage UI)
-- ============================================================================

-- Note: Storage buckets are better created via the Supabase dashboard
-- Go to Storage → New Bucket → Create "uploads" and "outputs" buckets
-- Set them as public if needed

-- ============================================================================
-- ADD SERVICE ROLE POLICY FOR USER_PROFILES
-- ============================================================================

-- First add unique constraint on user_id if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'user_profiles_user_id_key'
    ) THEN
        ALTER TABLE user_profiles 
        ADD CONSTRAINT user_profiles_user_id_key UNIQUE (user_id);
    END IF;
END $$;

-- Create helper function to create test user profiles (bypasses RLS)
CREATE OR REPLACE FUNCTION create_test_user_profile(
    p_user_id UUID,
    p_email TEXT,
    p_credits INTEGER DEFAULT 0
)
RETURNS VOID AS $$
BEGIN
    -- Insert with id = user_id to satisfy NOT NULL constraint on id column
    -- Use id as conflict target since it's the primary key
    INSERT INTO user_profiles (id, user_id, email, credits)
    VALUES (p_user_id, p_user_id, p_email, p_credits)
    ON CONFLICT (id) DO UPDATE
    SET user_id = p_user_id, email = p_email, credits = p_credits;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION create_test_user_profile TO authenticated, service_role;

"""
    
    full_sql = user_profiles_fix + "\n" + migration_sql + "\n" + storage_buckets
    
    # Copy to clipboard
    try:
        pyperclip.copy(full_sql)
        clipboard_status = "✓ SQL copied to clipboard!"
    except Exception as e:
        clipboard_status = f"✗ Could not copy to clipboard: {e}"
        print("\nSQL will be printed below instead.\n")
    
    # Print summary
    print(f"\nProject: {project_ref}")
    print(f"SQL Length: {len(full_sql)} characters")
    print(f"Lines: {full_sql.count(chr(10))} lines")
    print(f"\n{clipboard_status}")
    
    # Provide direct link
    sql_editor_url = f"https://supabase.com/dashboard/project/{project_ref}/sql/new"
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print(f"\n1. Open SQL Editor: {sql_editor_url}")
    print("2. Paste the SQL (Ctrl+V) - already in your clipboard!")
    print("3. Click 'Run' button")
    print("4. Come back and run tests:")
    print("   python tests/run_all_tests.py applications/asaad_000_MultiImageGenerator/.env")
    print("\n" + "=" * 80)
    
    # If clipboard failed, print SQL
    if "Could not copy" in clipboard_status:
        print("\n" + "=" * 80)
        print("SQL TO COPY:")
        print("=" * 80)
        print(full_sql)
        print("=" * 80)

if __name__ == "__main__":
    main()
