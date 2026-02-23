#!/usr/bin/env python3
"""
Run credit system database migration.

This script executes the migration SQL against your Supabase database.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
env_file = Path(__file__).parent.parent.parent / "applications" / "asaad_000_MultiImageGenerator" / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✓ Loaded environment from: {env_file}")
else:
    print(f"✗ .env file not found: {env_file}")
    sys.exit(1)

# Get credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

if not supabase_url or not supabase_key:
    print("✗ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    sys.exit(1)

print(f"✓ Supabase URL: {supabase_url}")
print(f"✓ Service key loaded")

# Read migration SQL
migration_file = Path(__file__).parent / "migration.sql"
with open(migration_file, 'r', encoding='utf-8') as f:
    migration_sql = f.read()

print(f"\n✓ Loaded migration from: {migration_file}")
print(f"  Migration size: {len(migration_sql)} characters")

# Create Supabase client
try:
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✓ Connected to Supabase")
except Exception as e:
    print(f"✗ Failed to connect to Supabase: {e}")
    sys.exit(1)

# Check if user_profiles table exists
print("\n" + "=" * 80)
print("CHECKING DATABASE STATE")
print("=" * 80)

try:
    # Try to query user_profiles
    result = supabase.table('user_profiles').select('*').limit(1).execute()
    print("✓ user_profiles table exists")
except Exception as e:
    print(f"✗ user_profiles table not found or error: {e}")
    print("\nThe user_profiles table must exist before running this migration.")
    print("Please create it first or run your application's initial migration.")
    
    # Offer to create basic user_profiles table
    response = input("\nCreate basic user_profiles table? (yes/no): ").strip().lower()
    if response == 'yes':
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
            email TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Enable RLS
        ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
        
        -- Users can view their own profile
        CREATE POLICY "Users can view own profile"
            ON user_profiles
            FOR SELECT
            USING (auth.uid() = user_id);
        
        -- Users can update their own profile
        CREATE POLICY "Users can update own profile"
            ON user_profiles
            FOR UPDATE
            USING (auth.uid() = user_id);
        """
        
        try:
            supabase.postgrest.rpc('exec', {'sql': create_table_sql}).execute()
            print("✓ Created user_profiles table")
        except Exception as e:
            print(f"✗ Failed to create user_profiles: {e}")
            print("\nPlease create the table manually in Supabase SQL Editor.")
            sys.exit(1)
    else:
        sys.exit(1)

# Execute migration
print("\n" + "=" * 80)
print("RUNNING MIGRATION")
print("=" * 80)
print("\nThis will:")
print("  1. Add 'credits' column to user_profiles")
print("  2. Create credit_transactions table")
print("  3. Create RPC functions for credit operations")
print("  4. Set up Row Level Security policies")

response = input("\nProceed with migration? (yes/no): ").strip().lower()
if response != 'yes':
    print("Migration cancelled.")
    sys.exit(0)

print("\nExecuting migration...")
print("Note: You'll need to run this SQL in Supabase SQL Editor manually.\n")
print("=" * 80)
print("COPY THIS SQL AND RUN IN SUPABASE SQL EDITOR:")
print("=" * 80)
print(migration_sql)
print("=" * 80)

print("\nInstructions:")
print("1. Go to https://supabase.com/dashboard/project/_/sql/new")
print("2. Copy the SQL above")
print("3. Paste it into the SQL Editor")
print("4. Click 'Run' to execute")
print("5. Come back here and run tests again!")

print("\nAfter running the migration, test with:")
print(f"  python tests/run_all_tests.py {env_file}")
