"""
Shared authentication module for all AsaadAsh applications

Provides provider-agnostic authentication with support for:
- Multiple auth providers (Supabase, Auth0, Firebase, etc.)
- Decorators for protecting routes
- User session management
- Token validation

Usage:
    from shared.auth import require_auth, get_current_user, optional_auth
    
    @app.route('/api/protected')
    @require_auth
    def protected_route():
        user = get_current_user()
        return {'message': f'Hello {user["email"]}'}
"""

from .decorators import require_auth, optional_auth, require_role
from .supabase import SupabaseAuth
from .base import AuthProvider, get_auth_provider, get_current_user

__all__ = [
    'require_auth',
    'optional_auth',
    'require_role',
    'get_auth_provider',
    'get_current_user',
    'SupabaseAuth',
    'AuthProvider',
]
