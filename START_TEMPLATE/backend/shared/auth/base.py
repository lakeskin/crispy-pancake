"""
Base authentication provider interface
All auth providers must implement this interface
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from flask import request, g
import os
from pathlib import Path
import yaml


class AuthProvider(ABC):
    """Abstract base class for authentication providers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize auth provider with configuration
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from shared/auth/config.yaml"""
        try:
            config_path = Path(__file__).parent / 'config.yaml'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    global_config = yaml.safe_load(f)
                    # Merge with instance config (instance config takes precedence)
                    self.config = {**global_config, **self.config}
        except Exception as e:
            print(f"Warning: Could not load auth config: {e}")
    
    @abstractmethod
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify authentication token and return user data
        
        Args:
            token: JWT or session token
            
        Returns:
            User data dict if valid, None if invalid
        """
        pass
    
    @abstractmethod
    def sign_up(self, email: str, password: str, **kwargs) -> Dict[str, Any]:
        """
        Create new user account
        
        Args:
            email: User email
            password: User password
            **kwargs: Additional user metadata
            
        Returns:
            Dict with user data and session token
        """
        pass
    
    @abstractmethod
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Sign in existing user
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dict with user data and session token
        """
        pass
    
    @abstractmethod
    def sign_out(self, token: str) -> bool:
        """
        Sign out user and invalidate token
        
        Args:
            token: Current session token
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh expired access token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict with new access token
        """
        pass
    
    @abstractmethod
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User data dict if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_user(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Update user data
        
        Args:
            user_id: User ID
            **kwargs: Fields to update
            
        Returns:
            Updated user data
        """
        pass


# Global auth provider instance
_auth_provider: Optional[AuthProvider] = None


def get_auth_provider() -> AuthProvider:
    """
    Get the global auth provider instance
    
    Returns:
        Configured AuthProvider instance
    """
    global _auth_provider
    
    if _auth_provider is None:
        # Determine provider from environment or config
        provider_name = os.getenv('AUTH_PROVIDER', 'supabase').lower()
        
        if provider_name == 'supabase':
            from .supabase import SupabaseAuth
            _auth_provider = SupabaseAuth()
        else:
            raise ValueError(f"Unsupported auth provider: {provider_name}")
    
    return _auth_provider


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from request context
    
    Returns:
        User data dict if authenticated, None otherwise
    """
    return getattr(g, 'current_user', None)


def set_current_user(user: Dict[str, Any]):
    """
    Set current user in request context
    
    Args:
        user: User data dict
    """
    g.current_user = user
