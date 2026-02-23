"""
Database Manager for Supabase.

Handles table creation, schema management, and SQL execution.
"""

import os
from typing import Dict, List, Optional, Any
from supabase import Client


class DatabaseManager:
    """Manage Supabase database tables and schema"""
    
    def __init__(self, client: Client):
        """
        Initialize database manager.
        
        Args:
            client: Authenticated Supabase client
        """
        self.client = client
    
    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """
        Execute raw SQL query.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Result dictionary with success status and data
            
        Example:
            >>> manager = DatabaseManager(client)
            >>> result = manager.execute_sql("SELECT version()")
            >>> print(result['data'])
        """
        try:
            # Use Supabase REST API to execute SQL
            # Note: This requires the SQL to be run through Supabase dashboard or REST API
            response = self.client.postgrest.rpc('exec_sql', {'query': sql}).execute()
            return {
                'success': True,
                'data': response.data if hasattr(response, 'data') else None,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
            
        Example:
            >>> if manager.table_exists('user_profiles'):
            ...     print("Table exists")
        """
        try:
            result = self.client.table(table_name).select('*').limit(1).execute()
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if 'does not exist' in error_msg or 'not found' in error_msg:
                return False
            # Some other error occurred
            raise
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get list of columns in a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names
            
        Example:
            >>> columns = manager.get_table_columns('user_profiles')
            >>> print(columns)
            ['id', 'email', 'credits', 'created_at']
        """
        try:
            result = self.client.table(table_name).select('*').limit(1).execute()
            if result.data:
                return list(result.data[0].keys())
            return []
        except Exception as e:
            raise Exception(f"Failed to get columns for table '{table_name}': {e}")
    
    def create_user_profiles_table(self) -> str:
        """
        Get SQL to create user_profiles table with proper schema.
        
        Returns:
            SQL string to execute in Supabase SQL editor
            
        Example:
            >>> sql = manager.create_user_profiles_table()
            >>> print(sql)
        """
        return """
-- Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    username TEXT UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    credits INTEGER DEFAULT 0 CHECK (credits >= 0),
    subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;

-- Users can view their own profile
CREATE POLICY "Users can view own profile"
    ON user_profiles
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own profile
CREATE POLICY "Users can insert own profile"
    ON user_profiles
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON user_profiles
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username);

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""
    
    def fix_existing_user_profiles_table(self) -> str:
        """
        Get SQL to fix existing user_profiles table to match expected schema.
        
        This adds missing columns without dropping existing data.
        
        Returns:
            SQL string to execute in Supabase SQL editor
            
        Example:
            >>> sql = manager.fix_existing_user_profiles_table()
            >>> print(sql)
        """
        return """
-- Fix existing user_profiles table
-- This safely adds missing columns without losing data

-- Add user_id column if it doesn't exist (links to auth.users)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_profiles' 
        AND column_name = 'user_id'
    ) THEN
        -- Add column
        ALTER TABLE user_profiles ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
        
        -- If there's an 'id' column, copy data and set as primary key
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'user_profiles' 
            AND column_name = 'id'
        ) THEN
            UPDATE user_profiles SET user_id = id WHERE user_id IS NULL;
            ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_pkey;
            ALTER TABLE user_profiles ADD PRIMARY KEY (user_id);
        END IF;
    END IF;
END $$;

-- Add email column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_profiles' 
        AND column_name = 'email'
    ) THEN
        ALTER TABLE user_profiles ADD COLUMN email TEXT;
    END IF;
END $$;

-- Add credits column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_profiles' 
        AND column_name = 'credits'
    ) THEN
        ALTER TABLE user_profiles ADD COLUMN credits INTEGER DEFAULT 0 CHECK (credits >= 0);
    ELSE
        -- Ensure the check constraint exists
        ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_credits_check;
        ALTER TABLE user_profiles ADD CONSTRAINT user_profiles_credits_check CHECK (credits >= 0);
    END IF;
END $$;

-- Add updated_at column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_profiles' 
        AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE user_profiles ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Enable RLS
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Update policies
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;

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
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);

-- Create or update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verification
DO $$
BEGIN
    ASSERT (SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_profiles' AND column_name = 'user_id'
    )), 'user_id column not found';
    
    ASSERT (SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_profiles' AND column_name = 'credits'
    )), 'credits column not found';
    
    RAISE NOTICE 'user_profiles table fixed successfully!';
END $$;
"""
    
    def verify_table_schema(self, table_name: str, required_columns: List[str]) -> Dict[str, Any]:
        """
        Verify that a table has all required columns.
        
        Args:
            table_name: Name of the table
            required_columns: List of column names that must exist
            
        Returns:
            Dictionary with verification results
            
        Example:
            >>> result = manager.verify_table_schema('user_profiles', ['user_id', 'email', 'credits'])
            >>> if result['valid']:
            ...     print("Schema is correct")
            ... else:
            ...     print(f"Missing: {result['missing_columns']}")
        """
        try:
            if not self.table_exists(table_name):
                return {
                    'valid': False,
                    'exists': False,
                    'missing_columns': required_columns,
                    'extra_columns': [],
                    'error': f"Table '{table_name}' does not exist"
                }
            
            actual_columns = self.get_table_columns(table_name)
            missing = [col for col in required_columns if col not in actual_columns]
            extra = [col for col in actual_columns if col not in required_columns]
            
            return {
                'valid': len(missing) == 0,
                'exists': True,
                'missing_columns': missing,
                'extra_columns': extra,
                'actual_columns': actual_columns,
                'error': None
            }
        except Exception as e:
            return {
                'valid': False,
                'exists': False,
                'missing_columns': [],
                'extra_columns': [],
                'error': str(e)
            }
    
    def get_migration_sql(self, migration_name: str) -> Optional[str]:
        """
        Load a migration SQL file.
        
        Args:
            migration_name: Name of the migration (e.g., 'credits', 'payments')
            
        Returns:
            SQL string or None if not found
            
        Example:
            >>> sql = manager.get_migration_sql('credits')
            >>> if sql:
            ...     print("Migration loaded")
        """
        import os
        from pathlib import Path
        
        # Look for migration file
        base_dir = Path(__file__).parent.parent
        migration_paths = [
            base_dir / migration_name / 'migration.sql',
            base_dir / f'{migration_name}_migration.sql',
        ]
        
        for path in migration_paths:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        
        return None
