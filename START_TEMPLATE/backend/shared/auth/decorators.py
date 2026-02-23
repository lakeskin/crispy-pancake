"""
Authentication decorators for protecting Flask routes
"""

from functools import wraps
from flask import request, jsonify, g
from typing import Optional, List, Callable
from .base import get_auth_provider, set_current_user


def require_auth(f: Callable) -> Callable:
    """
    Decorator to require authentication for a route
    
    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected_route():
            user = get_current_user()
            return {'message': f'Hello {user["email"]}'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'No authorization header',
                'message': 'Authentication required'
            }), 401
        
        # Parse Bearer token
        try:
            scheme, token = auth_header.split(' ')
            if scheme.lower() != 'bearer':
                return jsonify({
                    'error': 'Invalid authorization scheme',
                    'message': 'Use Bearer token'
                }), 401
        except ValueError:
            return jsonify({
                'error': 'Invalid authorization header',
                'message': 'Format: Bearer <token>'
            }), 401
        
        # Verify token
        auth_provider = get_auth_provider()
        user = auth_provider.verify_token(token)
        
        if not user:
            return jsonify({
                'error': 'Invalid token',
                'message': 'Authentication failed'
            }), 401
        
        # Store user in request context
        set_current_user(user)
        
        # Call the actual route function
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f: Callable) -> Callable:
    """
    Decorator for optional authentication
    Route will execute regardless, but user data will be available if authenticated
    
    Usage:
        @app.route('/api/optional')
        @optional_auth
        def optional_route():
            user = get_current_user()
            if user:
                return {'message': f'Hello {user["email"]}'}
            return {'message': 'Hello guest'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try to extract token
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                scheme, token = auth_header.split(' ')
                if scheme.lower() == 'bearer':
                    # Verify token
                    auth_provider = get_auth_provider()
                    user = auth_provider.verify_token(token)
                    if user:
                        set_current_user(user)
            except (ValueError, Exception):
                # Silently fail for optional auth
                pass
        
        # Call route function regardless of auth status
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(roles: List[str]) -> Callable:
    """
    Decorator to require specific role(s) for a route
    
    Usage:
        @app.route('/api/admin')
        @require_role(['admin', 'moderator'])
        def admin_route():
            return {'message': 'Admin area'}
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First verify authentication
            auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                return jsonify({
                    'error': 'No authorization header',
                    'message': 'Authentication required'
                }), 401
            
            try:
                scheme, token = auth_header.split(' ')
                if scheme.lower() != 'bearer':
                    return jsonify({
                        'error': 'Invalid authorization scheme'
                    }), 401
            except ValueError:
                return jsonify({
                    'error': 'Invalid authorization header'
                }), 401
            
            # Verify token
            auth_provider = get_auth_provider()
            user = auth_provider.verify_token(token)
            
            if not user:
                return jsonify({
                    'error': 'Invalid token'
                }), 401
            
            # Check role
            user_role = user.get('role', 'user')
            if user_role not in roles:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'Required role: {", ".join(roles)}'
                }), 403
            
            # Store user in context
            set_current_user(user)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator
