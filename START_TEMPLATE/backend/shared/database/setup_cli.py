#!/usr/bin/env python3
"""
Automated setup using Supabase CLI.

This script uses the Supabase CLI to execute SQL without manual intervention.
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return None

def main():
    print("=" * 80)
    print("AUTOMATED SUPABASE SETUP WITH CLI")
    print("=" * 80)
    
    # Check if supabase CLI is installed
    print("\nChecking for Supabase CLI...")
    version = run_command("supabase --version")
    if version:
        print(f"✓ Supabase CLI found: {version.strip()}")
    else:
        print("✗ Supabase CLI not installed!")
        print("\nInstall it with:")
        print("  npm install -g supabase")
        print("OR:")
        print("  scoop install supabase")
        sys.exit(1)
    
    # Load environment
    env_file = Path(__file__).parent.parent.parent / "applications" / "asaad_000_MultiImageGenerator" / ".env"
    load_dotenv(env_file)
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    db_password = os.getenv('SUPABASE_DB_PASSWORD')
    
    if not all([url, key, db_password]):
        print("✗ Missing environment variables")
        sys.exit(1)
    
    project_ref = url.split('//')[1].split('.')[0]
    
    print(f"\n✓ Project: {project_ref}")
    
    # Link to project
    print("\n Linking to Supabase project...")
    link_cmd = f'supabase link --project-ref {project_ref} --password "{db_password}"'
    if run_command(link_cmd):
        print("✓ Project linked")
    else:
        print("✗ Failed to link project")
        sys.exit(1)
    
    # Run migrations
    print("\nRunning database migrations...")
    
    # Create migrations directory if not exists
    migrations_dir = Path(__file__).parent / "migrations"
    migrations_dir.mkdir(exist_ok=True)
    
    # Copy SQL files to migrations
    migration_file = Path(__file__).parent.parent / "credits" / "migration.sql"
    
    if migration_file.exists():
        # Create numbered migration
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        migration_dest = migrations_dir / f"{timestamp}_credit_system.sql"
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # Add user_profiles fix
        user_profiles_fix = """
-- Fix user_profiles
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email TEXT;
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

"""
        
        full_sql = user_profiles_fix + sql
        
        with open(migration_dest, 'w', encoding='utf-8') as f:
            f.write(full_sql)
        
        print(f"✓ Migration file created: {migration_dest}")
        
        # Apply migration
        print("\nApplying migrations...")
        result = run_command(f"supabase db push")
        if result:
            print("✓ Migrations applied successfully!")
        else:
            print("✗ Failed to apply migrations")
            sys.exit(1)
    
    print("\n" + "=" * 80)
    print("✓ SETUP COMPLETE!")
    print("=" * 80)
    print("\nRun tests: python tests/run_all_tests.py applications/asaad_000_MultiImageGenerator/.env")

if __name__ == "__main__":
    main()
