"""
Supabase authentication provider implementation
"""

from typing import Optional, Dict, Any
import os
import jwt
import requests
from datetime import datetime, timedelta
from .base import AuthProvider
from supabase import create_client, Client


class SupabaseAuth(AuthProvider):
    """Supabase authentication provider"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Supabase auth with configuration"""
        super().__init__(config)
        
        # Get Supabase credentials from environment
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.jwt_secret = os.getenv('SUPABASE_JWT_SECRET')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment"
            )
        
        # API endpoints
        self.auth_url = f"{self.supabase_url}/auth/v1"
        self.rest_url = f"{self.supabase_url}/rest/v1"
        
        # Headers for API requests
        self.headers = {
            'apikey': self.supabase_key,
            'Content-Type': 'application/json'
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and return user data
        
        Args:
            token: JWT access token
            
        Returns:
            User data if valid, None if invalid
        """
        try:
            # If we have JWT secret, verify locally (faster)
            if self.jwt_secret:
                payload = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=['HS256'],
                    options={
                        'verify_signature': True,
                        'verify_exp': True
                    }
                )
                return {
                    'id': payload.get('sub'),
                    'email': payload.get('email'),
                    'role': payload.get('role'),
                    'metadata': payload.get('user_metadata', {}),
                    'app_metadata': payload.get('app_metadata', {})
                }
            else:
                # Fallback: verify with Supabase API
                response = requests.get(
                    f"{self.auth_url}/user",
                    headers={
                        **self.headers,
                        'Authorization': f'Bearer {token}'
                    }
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        'id': user_data.get('id'),
                        'email': user_data.get('email'),
                        'role': user_data.get('role'),
                        'metadata': user_data.get('user_metadata', {}),
                        'app_metadata': user_data.get('app_metadata', {})
                    }
                
                return None
                
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            print(f"Token verification error: {e}")
            return None
    
    def sign_up(self, email: str, password: str, **kwargs) -> Dict[str, Any]:
        """
        Create new user account
        
        Args:
            email: User email
            password: User password
            **kwargs: Additional metadata (name, etc.)
            
        Returns:
            Dict with user data and session
        """
        payload = {
            'email': email,
            'password': password,
            'data': kwargs  # User metadata
        }
        
        response = requests.post(
            f"{self.auth_url}/signup",
            json=payload,
            headers=self.headers
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # Check if email confirmation is required
            user_data = data.get('user', {})
            session_data = data.get('session')
            
            # If session is None, email confirmation is required
            if session_data is None:
                return {
                    'user': {
                        'id': user_data.get('id'),
                        'email': user_data.get('email'),
                        'metadata': user_data.get('user_metadata', {}),
                        'email_confirmed': False
                    },
                    'session': None,
                    'message': 'Please check your email to confirm your account'
                }
            
            # Email confirmation disabled - return full session
            return {
                'user': {
                    'id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'metadata': user_data.get('user_metadata', {}),
                    'email_confirmed': True
                },
                'session': {
                    'access_token': data.get('access_token'),
                    'refresh_token': data.get('refresh_token'),
                    'expires_at': data.get('expires_at')
                }
            }
        else:
            error = response.json()
            raise Exception(f"Sign up failed: {error.get('msg', 'Unknown error')}")
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Sign in existing user
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dict with user data and session
        """
        payload = {
            'email': email,
            'password': password
        }
        
        response = requests.post(
            f"{self.auth_url}/token?grant_type=password",
            json=payload,
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                'user': {
                    'id': data.get('user', {}).get('id'),
                    'email': data.get('user', {}).get('email'),
                    'metadata': data.get('user', {}).get('user_metadata', {}),
                    'role': data.get('user', {}).get('role')
                },
                'session': {
                    'access_token': data.get('access_token'),
                    'refresh_token': data.get('refresh_token'),
                    'expires_at': data.get('expires_at'),
                    'expires_in': data.get('expires_in')
                }
            }
        else:
            error = response.json()
            raise Exception(f"Sign in failed: {error.get('msg', 'Invalid credentials')}")
    
    def sign_out(self, token: str) -> bool:
        """
        Sign out user and invalidate token
        
        Args:
            token: Access token to invalidate
            
        Returns:
            True if successful
        """
        try:
            response = requests.post(
                f"{self.auth_url}/logout",
                headers={
                    **self.headers,
                    'Authorization': f'Bearer {token}'
                }
            )
            return response.status_code == 204
        except Exception:
            return False
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh expired access token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict with new access token
        """
        payload = {
            'refresh_token': refresh_token
        }
        
        response = requests.post(
            f"{self.auth_url}/token?grant_type=refresh_token",
            json=payload,
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'expires_at': data.get('expires_at'),
                'expires_in': data.get('expires_in')
            }
        else:
            error = response.json()
            raise Exception(f"Token refresh failed: {error.get('msg', 'Unknown error')}")
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data by ID (admin operation)
        
        Args:
            user_id: User ID
            
        Returns:
            User data if found
        """
        try:
            response = requests.get(
                f"{self.auth_url}/admin/users/{user_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'role': user_data.get('role'),
                    'metadata': user_data.get('user_metadata', {}),
                    'created_at': user_data.get('created_at')
                }
            return None
        except Exception:
            return None
    
    def update_user(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Update user data (admin operation)
        
        Args:
            user_id: User ID
            **kwargs: Fields to update
            
        Returns:
            Updated user data
        """
        payload = {}
        
        if 'email' in kwargs:
            payload['email'] = kwargs['email']
        if 'password' in kwargs:
            payload['password'] = kwargs['password']
        if 'metadata' in kwargs:
            payload['user_metadata'] = kwargs['metadata']
        
        response = requests.put(
            f"{self.auth_url}/admin/users/{user_id}",
            json=payload,
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                'id': data.get('id'),
                'email': data.get('email'),
                'metadata': data.get('user_metadata', {})
            }
        else:
            error = response.json()
            raise Exception(f"User update failed: {error.get('msg', 'Unknown error')}")


# ============================================================================
# CONVENIENCE FUNCTIONS FOR TESTING AND SIMPLE USE CASES
# ============================================================================

# Module-level Supabase client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance
    
    Returns:
        Supabase client
    """
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment"
            )
        
        _supabase_client = create_client(supabase_url, supabase_key)
    
    return _supabase_client


def signup_user(email: str, password: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to sign up a new user
    
    Args:
        email: User email
        password: User password
        **kwargs: Additional user metadata
        
    Returns:
        Dict with user data and session
        
    Example:
        >>> result = signup_user("user@example.com", "password123", name="John Doe")
        >>> user_id = result['user']['id']
        >>> access_token = result['session']['access_token']
    """
    try:
        client = get_supabase_client()
        response = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": kwargs  # User metadata
            }
        })
        
        if response.user:
            return {
                'user': {
                    'id': response.user.id,
                    'email': response.user.email,
                    'metadata': response.user.user_metadata or {},
                    'email_confirmed': response.user.email_confirmed_at is not None
                },
                'session': {
                    'access_token': response.session.access_token if response.session else None,
                    'refresh_token': response.session.refresh_token if response.session else None,
                    'expires_at': response.session.expires_at if response.session else None
                } if response.session else None,
                'message': 'Please check your email to confirm your account' if not response.session else 'Sign up successful'
            }
        else:
            raise Exception("Sign up failed: No user returned")
            
    except Exception as e:
        raise Exception(f"Sign up failed: {str(e)}")


def login_user(email: str, password: str) -> Dict[str, Any]:
    """
    Convenience function to log in a user
    
    Args:
        email: User email
        password: User password
        
    Returns:
        Dict with user data and session
        
    Example:
        >>> result = login_user("user@example.com", "password123")
        >>> user_id = result['user']['id']
        >>> access_token = result['session']['access_token']
    """
    try:
        client = get_supabase_client()
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            return {
                'user': {
                    'id': response.user.id,
                    'email': response.user.email,
                    'metadata': response.user.user_metadata or {},
                    'role': response.user.role if hasattr(response.user, 'role') else None
                },
                'session': {
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at,
                    'expires_in': response.session.expires_in
                }
            }
        else:
            raise Exception("Login failed: No user returned")
            
    except Exception as e:
        raise Exception(f"Login failed: {str(e)}")


def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get user profile by ID
    
    Args:
        user_id: User ID
        
    Returns:
        User data if found, None otherwise
        
    Example:
        >>> profile = get_user_profile("user-id-123")
        >>> if profile:
        ...     print(profile['email'])
    """
    try:
        client = get_supabase_client()
        
        # Use admin API to get user
        # Note: This requires SUPABASE_SERVICE_KEY to be set
        response = client.auth.admin.get_user_by_id(user_id)
        
        if response.user:
            return {
                'id': response.user.id,
                'email': response.user.email,
                'metadata': response.user.user_metadata or {},
                'role': response.user.role if hasattr(response.user, 'role') else None,
                'created_at': str(response.user.created_at) if hasattr(response.user, 'created_at') else None
            }
        
        return None
        
    except Exception as e:
        print(f"Failed to get user profile: {e}")
        return None


def delete_user(user_id: str) -> bool:
    """
    Convenience function to delete a user (admin operation)
    
    Args:
        user_id: User ID to delete
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> success = delete_user("user-id-123")
        >>> if success:
        ...     print("User deleted")
    """
    try:
        client = get_supabase_client()
        
        # Use admin API to delete user
        # Note: This requires SUPABASE_SERVICE_KEY to be set
        client.auth.admin.delete_user(user_id)
        return True
        
    except Exception as e:
        print(f"Failed to delete user: {e}")
        return False


def request_password_reset(email: str, redirect_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Request a password reset email for a user
    
    Args:
        email: User's email address
        redirect_url: Optional URL to redirect to after reset (default: app's reset page)
        
    Returns:
        Dict with success status and message
        
    Example:
        >>> result = request_password_reset("user@example.com")
        >>> if result['success']:
        ...     print("Reset email sent")
    """
    try:
        client = get_supabase_client()
        
        # Set redirect URL if provided, otherwise use default
        options = {}
        if redirect_url:
            options['redirect_to'] = redirect_url
        
        # Request password reset - using correct method name
        client.auth.reset_password_for_email(email, options)
        
        return {
            'success': True,
            'message': 'Password reset email sent. Please check your inbox.'
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to send reset email: {str(e)}'
        }


def update_password(new_password: str, access_token: Optional[str] = None, refresh_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Update user's password (requires valid session or reset token)
    
    Args:
        new_password: New password to set
        access_token: Access token from reset email link
        refresh_token: Refresh token from reset email link
        
    Returns:
        Dict with success status and message
        
    Example:
        >>> result = update_password("newSecurePassword123!", access_token, refresh_token)
        >>> if result['success']:
        ...     print("Password updated successfully")
    """
    try:
        client = get_supabase_client()
        
        # If tokens provided, set the session first (required for password reset flow)
        if access_token and refresh_token:
            # Set session using both tokens from the reset email link
            client.auth.set_session(access_token, refresh_token)
        elif access_token:
            # Try with just access token (may not work for all cases)
            # Create a minimal session
            client.auth.set_session(access_token, access_token)  # Some versions allow this
        
        # Update password
        response = client.auth.update_user({'password': new_password})
        
        if response.user:
            return {
                'success': True,
                'message': 'Password updated successfully',
                'user': {
                    'id': response.user.id,
                    'email': response.user.email
                }
            }
        else:
            return {
                'success': False,
                'message': 'Failed to update password'
            }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to update password: {str(e)}'
        }

