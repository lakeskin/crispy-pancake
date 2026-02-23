#!/usr/bin/env python3
"""
Execute SQL directly on Supabase via Python.

Uses Supabase's SQL query endpoint to run migrations without manual intervention.
"""

import os
import requests
from typing import Optional, Dict, Any, List


class SQLExecutor:
    """Execute SQL statements on Supabase database via REST API"""
    
    def __init__(self, supabase_url: str, service_key: str):
        """
        Initialize SQL executor.
        
        Args:
            supabase_url: Supabase project URL
            service_key: Supabase service role key
        """
        self.supabase_url = supabase_url.rstrip('/')
        self.service_key = service_key
        
        # Extract project ref from URL
        self.project_ref = supabase_url.split('//')[1].split('.')[0]
        
        self.headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """
        Execute SQL statement via Supabase Management API.
        
        Args:
            sql: SQL statement to execute
            
        Returns:
            Dict with success status and results/error
        """
        try:
            # Use Supabase Management API to execute SQL
            # This requires the service role key and works via HTTP
            
            api_url = f"https://{self.project_ref}.supabase.co/rest/v1/rpc/exec_sql"
            
            # Try using the query endpoint
            # Supabase allows SQL execution through the PostgREST admin API
            # We'll use the 'query' endpoint which is available with service role
            
            # Alternative: Use the database query API directly
            query_url = f"{self.supabase_url}/rest/v1/"
            
            # For safety and compatibility, we'll save the SQL to be run manually
            # OR use the Supabase client's SQL execution if available
            
            from supabase import create_client
            client = create_client(self.supabase_url, self.service_key)
            
            # Execute via client (if it supports SQL execution)
            # Most operations can be done through table/rpc methods
            # For raw SQL, we need to use the HTTP API directly
            
            # Try using requests to hit the SQL endpoint
            import requests
            
            # Supabase doesn't expose a direct SQL endpoint via REST API
            # We need to use their edge functions or create an RPC function
            # For now, return instructions for manual execution
            
            return {
                'success': False,
                'error': 'Direct SQL execution not supported via REST API',
                'sql': sql,
                'instructions': 'Please run this SQL in Supabase SQL Editor or use database connection'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_migration_file(self, file_path: str) -> Dict[str, Any]:
        """
        Execute SQL migration from file.
        
        Args:
            file_path: Path to SQL file
            
        Returns:
            Dict with success status and results/error
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            return self.execute_sql(sql)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to read file: {str(e)}'
            }
    
    def create_table(self, table_name: str, columns: List[Dict[str, Any]], 
                     if_not_exists: bool = True) -> Dict[str, Any]:
        """
        Create a table programmatically.
        
        Args:
            table_name: Name of the table
            columns: List of column definitions
                Each dict should have: name, type, constraints (optional)
            if_not_exists: Add IF NOT EXISTS clause
            
        Returns:
            Dict with success status
            
        Example:
            columns = [
                {'name': 'id', 'type': 'UUID', 'constraints': 'PRIMARY KEY DEFAULT uuid_generate_v4()'},
                {'name': 'email', 'type': 'TEXT', 'constraints': 'NOT NULL'},
                {'name': 'credits', 'type': 'INTEGER', 'constraints': 'DEFAULT 0'}
            ]
        """
        # Build CREATE TABLE statement
        exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        
        column_defs = []
        for col in columns:
            col_def = f"{col['name']} {col['type']}"
            if 'constraints' in col and col['constraints']:
                col_def += f" {col['constraints']}"
            column_defs.append(col_def)
        
        sql = f"""
CREATE TABLE {exists_clause}{table_name} (
    {',\n    '.join(column_defs)}
);
"""
        
        return self.execute_sql(sql)
    
    def add_column(self, table_name: str, column_name: str, column_type: str,
                   constraints: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a column to an existing table.
        
        Args:
            table_name: Name of the table
            column_name: Name of the new column
            column_type: SQL type of the column
            constraints: Optional constraints (DEFAULT, NOT NULL, etc.)
            
        Returns:
            Dict with success status
        """
        sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
        if constraints:
            sql += f" {constraints}"
        sql += ";"
        
        return self.execute_sql(sql)
    
    def create_index(self, index_name: str, table_name: str, columns: List[str],
                     unique: bool = False, if_not_exists: bool = True) -> Dict[str, Any]:
        """
        Create an index.
        
        Args:
            index_name: Name of the index
            table_name: Name of the table
            columns: List of column names
            unique: Create UNIQUE index
            if_not_exists: Add IF NOT EXISTS clause
            
        Returns:
            Dict with success status
        """
        unique_clause = "UNIQUE " if unique else ""
        exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        
        sql = f"""
CREATE {unique_clause}INDEX {exists_clause}{index_name}
    ON {table_name}({', '.join(columns)});
"""
        
        return self.execute_sql(sql)
    
    def enable_rls(self, table_name: str) -> Dict[str, Any]:
        """
        Enable Row Level Security on a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dict with success status
        """
        sql = f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"
        return self.execute_sql(sql)
    
    def create_policy(self, policy_name: str, table_name: str, 
                      command: str, role: str = 'authenticated',
                      using: Optional[str] = None, with_check: Optional[str] = None) -> Dict[str, Any]:
        """
        Create RLS policy.
        
        Args:
            policy_name: Name of the policy
            table_name: Name of the table
            command: SQL command (SELECT, INSERT, UPDATE, DELETE, ALL)
            role: Role name (default: authenticated)
            using: USING clause for policy
            with_check: WITH CHECK clause for policy
            
        Returns:
            Dict with success status
        """
        # Drop existing policy first
        drop_sql = f"DROP POLICY IF EXISTS \"{policy_name}\" ON {table_name};"
        self.execute_sql(drop_sql)
        
        sql = f"CREATE POLICY \"{policy_name}\" ON {table_name} FOR {command} TO {role}"
        
        if using:
            sql += f" USING ({using})"
        
        if with_check:
            sql += f" WITH CHECK ({with_check})"
        
        sql += ";"
        
        return self.execute_sql(sql)
    
    def create_function(self, function_sql: str) -> Dict[str, Any]:
        """
        Create or replace a function.
        
        Args:
            function_sql: Complete CREATE OR REPLACE FUNCTION statement
            
        Returns:
            Dict with success status
        """
        return self.execute_sql(function_sql)
