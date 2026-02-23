"""
Storage Manager for Supabase.

Handles storage bucket creation and management.
"""

from typing import Dict, List, Optional, Any
from supabase import Client


class StorageManager:
    """Manage Supabase storage buckets"""
    
    def __init__(self, client: Client):
        """
        Initialize storage manager.
        
        Args:
            client: Authenticated Supabase client
        """
        self.client = client
    
    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a storage bucket exists.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            True if bucket exists, False otherwise
            
        Example:
            >>> if storage.bucket_exists('uploads'):
            ...     print("Bucket exists")
        """
        try:
            self.client.storage.get_bucket(bucket_name)
            return True
        except Exception:
            return False
    
    def create_bucket(self, 
                     bucket_name: str, 
                     public: bool = False,
                     file_size_limit: Optional[int] = None,
                     allowed_mime_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a storage bucket.
        
        Args:
            bucket_name: Name of the bucket to create
            public: Whether bucket is publicly accessible
            file_size_limit: Max file size in bytes (None = no limit)
            allowed_mime_types: List of allowed MIME types (None = all types)
            
        Returns:
            Result dictionary with success status
            
        Example:
            >>> result = storage.create_bucket(
            ...     'user-uploads',
            ...     public=False,
            ...     file_size_limit=10 * 1024 * 1024,  # 10MB
            ...     allowed_mime_types=['image/jpeg', 'image/png']
            ... )
            >>> if result['success']:
            ...     print(f"Created bucket: {result['bucket_name']}")
        """
        try:
            if self.bucket_exists(bucket_name):
                return {
                    'success': True,
                    'bucket_name': bucket_name,
                    'exists': True,
                    'created': False,
                    'message': f"Bucket '{bucket_name}' already exists"
                }
            
            options = {
                'public': public
            }
            
            if file_size_limit:
                options['fileSizeLimit'] = file_size_limit
            
            if allowed_mime_types:
                options['allowedMimeTypes'] = allowed_mime_types
            
            self.client.storage.create_bucket(bucket_name, options)
            
            return {
                'success': True,
                'bucket_name': bucket_name,
                'exists': False,
                'created': True,
                'message': f"Created bucket '{bucket_name}'"
            }
            
        except Exception as e:
            return {
                'success': False,
                'bucket_name': bucket_name,
                'exists': False,
                'created': False,
                'error': str(e),
                'message': f"Failed to create bucket '{bucket_name}': {e}"
            }
    
    def delete_bucket(self, bucket_name: str, empty_first: bool = False) -> Dict[str, Any]:
        """
        Delete a storage bucket.
        
        Args:
            bucket_name: Name of the bucket to delete
            empty_first: Whether to empty bucket before deleting
            
        Returns:
            Result dictionary with success status
            
        Example:
            >>> result = storage.delete_bucket('old-bucket', empty_first=True)
            >>> if result['success']:
            ...     print("Bucket deleted")
        """
        try:
            if not self.bucket_exists(bucket_name):
                return {
                    'success': True,
                    'bucket_name': bucket_name,
                    'deleted': False,
                    'message': f"Bucket '{bucket_name}' does not exist"
                }
            
            if empty_first:
                self.empty_bucket(bucket_name)
            
            self.client.storage.delete_bucket(bucket_name)
            
            return {
                'success': True,
                'bucket_name': bucket_name,
                'deleted': True,
                'message': f"Deleted bucket '{bucket_name}'"
            }
            
        except Exception as e:
            return {
                'success': False,
                'bucket_name': bucket_name,
                'deleted': False,
                'error': str(e),
                'message': f"Failed to delete bucket '{bucket_name}': {e}"
            }
    
    def empty_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """
        Delete all files in a bucket.
        
        Args:
            bucket_name: Name of the bucket to empty
            
        Returns:
            Result dictionary with success status
            
        Example:
            >>> result = storage.empty_bucket('temp-uploads')
            >>> print(f"Deleted {result['files_deleted']} files")
        """
        try:
            # List all files
            files = self.client.storage.from_(bucket_name).list()
            
            if not files:
                return {
                    'success': True,
                    'bucket_name': bucket_name,
                    'files_deleted': 0,
                    'message': f"Bucket '{bucket_name}' is already empty"
                }
            
            # Delete all files
            file_paths = [f['name'] for f in files]
            self.client.storage.from_(bucket_name).remove(file_paths)
            
            return {
                'success': True,
                'bucket_name': bucket_name,
                'files_deleted': len(file_paths),
                'message': f"Deleted {len(file_paths)} files from bucket '{bucket_name}'"
            }
            
        except Exception as e:
            return {
                'success': False,
                'bucket_name': bucket_name,
                'files_deleted': 0,
                'error': str(e),
                'message': f"Failed to empty bucket '{bucket_name}': {e}"
            }
    
    def list_buckets(self) -> List[Dict[str, Any]]:
        """
        List all storage buckets.
        
        Returns:
            List of bucket information dictionaries
            
        Example:
            >>> buckets = storage.list_buckets()
            >>> for bucket in buckets:
            ...     print(f"{bucket['name']}: public={bucket['public']}")
        """
        try:
            buckets = self.client.storage.list_buckets()
            return [
                {
                    'name': bucket.name,
                    'id': bucket.id,
                    'public': bucket.public,
                    'created_at': bucket.created_at,
                    'updated_at': bucket.updated_at
                }
                for bucket in buckets
            ]
        except Exception as e:
            return []
    
    def get_bucket_info(self, bucket_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            Bucket information dictionary or None if not found
            
        Example:
            >>> info = storage.get_bucket_info('uploads')
            >>> if info:
            ...     print(f"Public: {info['public']}")
        """
        try:
            bucket = self.client.storage.get_bucket(bucket_name)
            return {
                'name': bucket.name,
                'id': bucket.id,
                'public': bucket.public,
                'created_at': bucket.created_at,
                'updated_at': bucket.updated_at,
                'file_size_limit': getattr(bucket, 'file_size_limit', None),
                'allowed_mime_types': getattr(bucket, 'allowed_mime_types', None)
            }
        except Exception:
            return None
    
    def setup_standard_buckets(self) -> Dict[str, Any]:
        """
        Create standard storage buckets for an application.
        
        Creates:
        - uploads (private): User uploads
        - outputs (public): Generated outputs
        - avatars (public): User avatars
        
        Returns:
            Result dictionary with creation status for each bucket
            
        Example:
            >>> results = storage.setup_standard_buckets()
            >>> for bucket, result in results['buckets'].items():
            ...     if result['success']:
            ...         print(f"✓ {bucket}")
        """
        buckets_config = [
            {
                'name': 'uploads',
                'public': False,
                'file_size_limit': 10 * 1024 * 1024,  # 10MB
                'allowed_mime_types': [
                    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                    'application/pdf', 'text/plain'
                ]
            },
            {
                'name': 'outputs',
                'public': True,
                'file_size_limit': 50 * 1024 * 1024,  # 50MB
                'allowed_mime_types': [
                    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                    'video/mp4', 'video/webm'
                ]
            },
            {
                'name': 'avatars',
                'public': True,
                'file_size_limit': 2 * 1024 * 1024,  # 2MB
                'allowed_mime_types': ['image/jpeg', 'image/png', 'image/webp']
            }
        ]
        
        results = {}
        all_success = True
        
        for config in buckets_config:
            bucket_name = config.pop('name')  # Remove name from config
            result = self.create_bucket(bucket_name, **config)
            results[bucket_name] = result
            if not result['success']:
                all_success = False
        
        return {
            'success': all_success,
            'buckets': results,
            'message': 'All buckets created successfully' if all_success else 'Some buckets failed to create'
        }
