#!/usr/bin/env python3
"""
Supabase storage bucket manager.

Creates and manages storage buckets via Python API.
"""

from typing import Dict, Any, List, Optional
from supabase import Client


class StorageManager:
    """Manage Supabase storage buckets"""
    
    def __init__(self, client: Client):
        """
        Initialize storage manager.
        
        Args:
            client: Supabase client instance
        """
        self.client = client
        self.storage = client.storage
    
    def create_bucket(self, bucket_name: str, public: bool = False,
                      file_size_limit: Optional[int] = None,
                      allowed_mime_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a storage bucket.
        
        Args:
            bucket_name: Name of the bucket
            public: Whether the bucket is publicly accessible
            file_size_limit: Max file size in bytes (optional)
            allowed_mime_types: List of allowed MIME types (optional)
            
        Returns:
            Dict with success status and bucket info
        """
        try:
            # Check if bucket exists
            try:
                existing = self.storage.get_bucket(bucket_name)
                return {
                    'success': True,
                    'bucket': existing,
                    'message': f'Bucket {bucket_name} already exists'
                }
            except:
                pass  # Bucket doesn't exist, create it
            
            # Create bucket
            options = {'public': public}
            
            if file_size_limit:
                options['file_size_limit'] = file_size_limit
            
            if allowed_mime_types:
                options['allowed_mime_types'] = allowed_mime_types
            
            result = self.storage.create_bucket(bucket_name, options)
            
            return {
                'success': True,
                'bucket': result,
                'message': f'Bucket {bucket_name} created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_buckets(self) -> Dict[str, Any]:
        """
        List all storage buckets.
        
        Returns:
            Dict with success status and bucket list
        """
        try:
            buckets = self.storage.list_buckets()
            return {
                'success': True,
                'buckets': buckets
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_bucket(self, bucket_name: str, empty_first: bool = True) -> Dict[str, Any]:
        """
        Delete a storage bucket.
        
        Args:
            bucket_name: Name of the bucket
            empty_first: Whether to empty the bucket first
            
        Returns:
            Dict with success status
        """
        try:
            if empty_first:
                # Empty bucket first
                self.storage.empty_bucket(bucket_name)
            
            # Delete bucket
            self.storage.delete_bucket(bucket_name)
            
            return {
                'success': True,
                'message': f'Bucket {bucket_name} deleted successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def set_bucket_public(self, bucket_name: str, public: bool = True) -> Dict[str, Any]:
        """
        Update bucket public status.
        
        Args:
            bucket_name: Name of the bucket
            public: Whether to make the bucket public
            
        Returns:
            Dict with success status
        """
        try:
            self.storage.update_bucket(bucket_name, {'public': public})
            
            return {
                'success': True,
                'message': f'Bucket {bucket_name} updated to public={public}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
