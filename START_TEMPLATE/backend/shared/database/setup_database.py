#!/usr/bin/env python3
"""
Comprehensive Supabase database setup tool.

This script:
1. Creates user_profiles table with correct schema
2. Runs credit system migration
3. Sets up storage buckets
4. Verifies everything is working
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Add parent directory to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.database import DatabaseManager, StorageManager

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 80}")
    print(f"{text.center(80)}")
    print(f"{'=' * 80}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def load_environment():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent.parent / "applications" / "asaad_000_MultiImageGenerator" / ".env"
    
    if not env_file.exists():
        print_error(f".env file not found: {env_file}")
        sys.exit(1)
    
    load_dotenv(env_file)
    print_success(f"Loaded environment from: {env_file}")
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print_error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        sys.exit(1)
    
    print_success(f"Supabase URL: {supabase_url}")
    print_success("Service key loaded")
    
    return supabase_url, supabase_key

def get_client(url, key):
    """Create Supabase client"""
    try:
        client = create_client(url, key)
        print_success("Connected to Supabase")
        return client
    except Exception as e:
        print_error(f"Failed to connect: {e}")
        sys.exit(1)

def check_user_profiles(db_manager: DatabaseManager):
    """Check if user_profiles table exists and has correct schema"""
    print_header("CHECKING USER_PROFILES TABLE")
    
    required_columns = ['user_id', 'email', 'credits']
    result = db_manager.verify_table_schema('user_profiles', required_columns)
    
    if not result['exists']:
        print_error("user_profiles table does not exist")
        return False
    
    print_success("user_profiles table exists")
    print(f"  Columns: {', '.join(result['actual_columns'])}")
    
    if result['missing_columns']:
        print_warning(f"Missing columns: {', '.join(result['missing_columns'])}")
        return False
    
    print_success("All required columns present")
    return True

# Removed - now using DatabaseManager

# Removed - now using DatabaseManager.get_migration_sql()

def setup_storage_buckets(storage_manager: StorageManager):
    """Setup storage buckets for uploads"""
    print_header("SETTING UP STORAGE BUCKETS")
    
    results = storage_manager.setup_standard_buckets()
    
    for bucket_name, result in results['buckets'].items():
        if result['success']:
            if result.get('created'):
                print_success(f"Created bucket '{bucket_name}'")
            else:
                print_success(f"Bucket '{bucket_name}' already exists")
        else:
            print_error(f"Failed to create bucket '{bucket_name}': {result.get('error', 'Unknown error')}")

def verify_setup(client):
    """Verify all setup is correct"""
    print_header("VERIFYING SETUP")
    
    checks = []
    
    # Check user_profiles table
    try:
        result = client.table('user_profiles').select('user_id,email,credits').limit(1).execute()
        print_success("user_profiles table accessible with correct columns")
        checks.append(True)
    except Exception as e:
        print_error(f"user_profiles verification failed: {e}")
        checks.append(False)
    
    # Check credit_transactions table
    try:
        result = client.table('credit_transactions').select('*').limit(1).execute()
        print_success("credit_transactions table accessible")
        checks.append(True)
    except Exception as e:
        print_error(f"credit_transactions verification failed: {e}")
        checks.append(False)
    
    # Check RPC functions exist
    functions = ['add_user_credits', 'deduct_user_credits', 'adjust_user_balance', 'get_user_credit_summary']
    for func in functions:
        try:
            # Try calling with dummy data to see if function exists
            # It will fail on validation but at least we know it exists
            client.rpc(func, {})
        except Exception as e:
            error_msg = str(e).lower()
            if 'not found' in error_msg or 'does not exist' in error_msg:
                print_error(f"RPC function '{func}' does not exist")
                checks.append(False)
            else:
                # Function exists but failed on validation (expected)
                print_success(f"RPC function '{func}' exists")
                checks.append(True)
    
    return all(checks)

def main():
    print_header("SUPABASE DATABASE SETUP TOOL")
    print("This tool will set up your Supabase database with all required tables,")
    print("functions, and storage buckets for the credit/payment system.")
    
    # Load environment
    url, key = load_environment()
    
    # Get client
    client = get_client(url, key)
    
    # Initialize managers
    db_manager = DatabaseManager(client)
    storage_manager = StorageManager(client)
    
    # Check current state
    has_user_profiles = check_user_profiles(db_manager)
    
    # Prepare SQL statements
    print_header("PREPARING SQL MIGRATIONS")
    
    sql_statements = []
    
    if not has_user_profiles:
        print_warning("user_profiles table needs to be created/fixed")
        sql_statements.append(("user_profiles", db_manager.fix_existing_user_profiles_table()))
    
    credit_migration = db_manager.get_migration_sql('credits')
    if credit_migration:
        sql_statements.append(("credit_system", credit_migration))
        print_success("Credit system migration loaded")
    
    if not sql_statements:
        print_success("All tables already exist!")
    else:
        print_header("SQL TO RUN IN SUPABASE SQL EDITOR")
        print(f"\nGo to: https://supabase.com/dashboard/project/{url.split('//')[-1].split('.')[0]}/sql/new\n")
        print(f"{Colors.YELLOW}Copy and paste the SQL below:{Colors.RESET}\n")
        print("=" * 80)
        
        for name, sql in sql_statements:
            print(f"\n-- {name.upper()} MIGRATION")
            print(sql)
            print("\n" + "=" * 80)
        
        print(f"\n{Colors.YELLOW}After running the SQL, press Enter to verify...{Colors.RESET}")
        input()
    
    # Setup storage
    setup_storage_buckets(storage_manager)
    
    # Verify everything
    if verify_setup(client):
        print_header("✓ SETUP COMPLETE!")
        print(f"\n{Colors.GREEN}All database tables, functions, and storage buckets are ready!{Colors.RESET}")
        print(f"\nYou can now run tests:")
        print(f"  python tests/run_all_tests.py applications/asaad_000_MultiImageGenerator/.env")
    else:
        print_header("✗ SETUP INCOMPLETE")
        print(f"\n{Colors.RED}Some components failed verification. Check errors above.{Colors.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
