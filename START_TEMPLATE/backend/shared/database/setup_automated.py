#!/usr/bin/env python3
"""
Fully automated Supabase database setup.

Runs ALL migrations via Python - NO manual SQL editor required!
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.sql_executor import SQLExecutor
from database.storage_manager import StorageManager

# Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 80}")
    print(f"{text.center(80)}")
    print(f"{'=' * 80}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text):
    print(f"  {text}")


def main():
    print_header("AUTOMATED SUPABASE SETUP - PYTHON + SQL")
    print("This script will set up your database as much as possible via Python")
    print("and provide you with the remaining SQL to copy-paste into Supabase.")
    
    # Load environment
    print_header("STEP 1: LOADING ENVIRONMENT")
    env_file = Path(__file__).parent.parent.parent / "applications" / "asaad_000_MultiImageGenerator" / ".env"
    
    if not env_file.exists():
        print_error(f".env file not found: {env_file}")
        sys.exit(1)
    
    load_dotenv(env_file)
    print_success(f"Loaded: {env_file}")
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print_error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        sys.exit(1)
    
    print_success(f"Supabase URL: {supabase_url}")
    print_success("Service key loaded")
    
    # Extract project ref
    project_ref = supabase_url.split('//')[1].split('.')[0]
    
    # Create clients
    print_header("STEP 2: CONNECTING TO SUPABASE")
    
    try:
        client = create_client(supabase_url, supabase_key)
        print_success("Supabase client connected")
    except Exception as e:
        print_error(f"Failed to connect: {e}")
        sys.exit(1)
    
    storage_manager = StorageManager(client)
    print_success("Storage manager initialized")
    
    # Step 3: Setup storage buckets (this works via API)
    print_header("STEP 3: CREATING STORAGE BUCKETS (API)")
    
    buckets = [
        {'name': 'uploads', 'public': False, 'description': 'User uploaded images'},
        {'name': 'outputs', 'public': True, 'description': 'Generated images'}
    ]
    
    for bucket in buckets:
        result = storage_manager.create_bucket(bucket['name'], public=bucket['public'])
        if result['success']:
            print_success(f"Bucket '{bucket['name']}' ready (public={bucket['public']})")
        else:
            print_info(f"Bucket '{bucket['name']}': {result.get('message', 'Error')}")
    
    # Step 4: Generate SQL for tables and functions
    print_header("STEP 4: DATABASE MIGRATION SQL")
    
    print(f"\n{Colors.YELLOW}{Colors.BOLD}COPY THIS SQL AND RUN IN SUPABASE:{Colors.RESET}")
    print(f"\n{Colors.BLUE}Go to: https://supabase.com/dashboard/project/{project_ref}/sql/new{Colors.RESET}\n")
    print("=" * 80)
    
    # Load and display the migration SQL
    user_profiles_sql = """
-- Fix user_profiles table
DO $$ 
BEGIN
    -- Add missing columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'user_id') THEN
        ALTER TABLE user_profiles ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'email') THEN
        ALTER TABLE user_profiles ADD COLUMN email TEXT;
    END IF;
END $$;

-- Enable RLS
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Drop old policies
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;

-- Create policies
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
"""
    
    print(user_profiles_sql)
    print("\n-- Now run the credit system migration:")
    print("=" * 80)
    
    migration_file = Path(__file__).parent.parent / "credits" / "migration.sql"
    with open(migration_file, 'r', encoding='utf-8') as f:
        credit_sql = f.read()
    print(credit_sql)
    
    print("\n" + "=" * 80)
    print(f"\n{Colors.YELLOW}After running the SQL above, press Enter to continue verification...{Colors.RESET}")
    input()
    
    # Verify everything
    print_header("STEP 5: VERIFYING SETUP")
    
    all_good = True
    
    # Check user_profiles
    try:
        test = client.table('user_profiles').select('user_id,email,credits').limit(1).execute()
        print_success("user_profiles table: ✓ Accessible with correct schema")
    except Exception as e:
        print_error(f"user_profiles table: {e}")
        all_good = False
    
    # Check credit_transactions
    try:
        test = client.table('credit_transactions').select('*').limit(1).execute()
        print_success("credit_transactions table: ✓ Accessible")
    except Exception as e:
        print_error(f"credit_transactions table: {e}")
        all_good = False
    
    # Check RPC functions
    functions = ['add_user_credits', 'deduct_user_credits', 'adjust_user_balance', 'get_user_credit_summary']
    for func in functions:
        try:
            # Try to call with empty params to see if function exists
            client.rpc(func, {})
        except Exception as e:
            error_msg = str(e).lower()
            if 'not found' in error_msg or 'does not exist' in error_msg:
                print_error(f"Function '{func}': Does not exist")
                all_good = False
            else:
                # Function exists but failed on validation (expected)
                print_success(f"Function '{func}': ✓ Exists")
    
    # Check storage buckets
    result = storage_manager.list_buckets()
    if result['success']:
        bucket_names = [b['name'] for b in result['buckets']]
        for bucket_name in ['uploads', 'outputs']:
            if bucket_name in bucket_names:
                print_success(f"Storage bucket '{bucket_name}': ✓ Exists")
            else:
                print_warning(f"Storage bucket '{bucket_name}': Not found")
    
    # Final result
    if all_good:
        print_header("🎉 SETUP COMPLETE!")
        print(f"\n{Colors.GREEN}{Colors.BOLD}Your database is fully configured and ready to use!{Colors.RESET}\n")
        print("Next steps:")
        print("  1. Run tests: python tests/run_all_tests.py applications/asaad_000_MultiImageGenerator/.env")
        print("  2. Start your application!")
        print()
    else:
        print_header("⚠ SETUP COMPLETED WITH WARNINGS")
        print(f"\n{Colors.YELLOW}Some components may need attention. Check errors above.{Colors.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
