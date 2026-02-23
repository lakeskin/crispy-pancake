# 🔐 Authentication Module

The authentication module provides provider-agnostic authentication with a Supabase implementation.

---

## 📦 Module Structure

```
shared/auth/
├── __init__.py           # Public exports
├── base.py               # Abstract AuthProvider interface
├── supabase.py           # Supabase implementation
├── decorators.py         # Flask route decorators
├── config.yaml           # Auth configuration
└── authStorage.js        # Frontend token storage (JS)
```

---

## 🚀 Quick Start

### Backend (Python/Flask)

```python
from shared.auth import require_auth, get_current_user

@app.route('/api/me')
@require_auth
def get_profile():
    user = get_current_user()
    return {
        'id': user['id'],
        'email': user['email'],
        'metadata': user.get('metadata', {})
    }
```

### Frontend (TypeScript/React)

```typescript
import { authStorage } from '../services/authStorage';

// After login
authStorage.setSession(session, rememberMe, user);

// Get tokens
const { accessToken, refreshToken } = authStorage.getTokens();

// Check if should refresh
if (authStorage.shouldRefreshToken()) {
    await refreshToken();
}
```

---

## 📖 API Reference

### Decorators

#### `@require_auth`
Requires valid authentication token. Returns 401 if not authenticated.

```python
from shared.auth import require_auth

@app.route('/api/protected')
@require_auth
def protected_route():
    user = get_current_user()
    return {'message': f'Hello {user["email"]}'}
```

#### `@optional_auth`
Captures authentication if present, but doesn't require it.

```python
from shared.auth import optional_auth

@app.route('/api/public')
@optional_auth
def public_route():
    user = get_current_user()
    if user:
        return {'greeting': f'Hello, {user["email"]}'}
    return {'greeting': 'Hello, guest'}
```

#### `@require_role(roles: List[str])`
Requires specific role(s).

```python
from shared.auth import require_role

@app.route('/api/admin')
@require_role(['admin', 'moderator'])
def admin_route():
    return {'message': 'Admin area'}
```

### Functions

#### `get_current_user() -> Optional[Dict]`
Returns current authenticated user from request context.

```python
user = get_current_user()
if user:
    print(user['id'])      # User ID
    print(user['email'])   # Email
    print(user['role'])    # Role (if set)
    print(user['metadata']) # User metadata
```

#### `get_auth_provider() -> AuthProvider`
Returns the configured auth provider instance.

```python
provider = get_auth_provider()
user_data = provider.verify_token(token)
```

---

## 🔧 Configuration

### config.yaml

```yaml
auth:
  provider: "supabase"
  
  session:
    cookie_name: "auth_token"
    cookie_secure: true
    cookie_httponly: true
    max_age: 604800  # 7 days (remember me)
    session_max_age: 3600  # 1 hour (no remember me)
  
  persistence:
    enabled: true
    default_remember_me: true
    refresh_threshold_seconds: 300
    auto_refresh: true
  
  tokens:
    verify_signature: true
    verify_expiry: true
    clock_skew_seconds: 60
  
  security:
    require_email_verification: true
    password_min_length: 8
```

### Environment Variables

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_JWT_SECRET=your-jwt-secret  # For local token verification
```

---

## 🔒 Token Verification

The module supports two verification methods:

### 1. Local JWT Verification (Fast)
If `SUPABASE_JWT_SECRET` is set, tokens are verified locally using the secret. This is faster as it doesn't require network calls.

### 2. API Verification (Fallback)
If JWT secret is not available, verification falls back to calling Supabase's `/auth/v1/user` endpoint.

---

## 📱 Frontend Auth Storage

### TypeScript Class

```typescript
import { authStorage } from '../services/authStorage';

// Configure (optional)
authStorage.configure({
    accessTokenKey: 'auth_token',
    refreshTokenKey: 'auth_refresh_token',
    refreshThresholdSeconds: 300,
});

// Store session after login
authStorage.setSession(session, rememberMe, user);

// Get current tokens
const { accessToken, refreshToken, expiresAt } = authStorage.getTokens();

// Get stored user
const user = authStorage.getUser();

// Check if token needs refresh
if (authStorage.shouldRefreshToken()) {
    // Call refresh endpoint
}

// Check if token is expired
if (authStorage.isTokenExpired()) {
    // Force re-login
}

// Clear on logout
authStorage.clear();
```

### Remember Me Functionality

When `rememberMe` is true:
- Tokens stored in `localStorage` (persist across browser sessions)

When `rememberMe` is false:
- Tokens stored in `sessionStorage` (cleared when browser closes)

---

## 🔄 Auth Flow

### Sign Up Flow

```
1. User submits email/password
2. Backend calls Supabase signup
3. If email confirmation enabled:
   - User receives confirmation email
   - After confirmation, user can log in
4. If email confirmation disabled:
   - Session returned immediately
   - User is logged in
```

### Login Flow

```
1. User submits email/password
2. Backend verifies with Supabase
3. Session returned with access_token + refresh_token
4. Frontend stores tokens (authStorage)
5. Tokens attached to subsequent requests
```

### Token Refresh Flow

```
1. Check if token expires soon (within threshold)
2. If yes, call refresh endpoint with refresh_token
3. Store new tokens
4. Continue with new access_token
```

---

## 🛡️ Route Protection Patterns

### Protected API Route

```python
from flask import Blueprint, jsonify
from shared.auth import require_auth, get_current_user

api = Blueprint('api', __name__)

@api.route('/profile')
@require_auth
def get_profile():
    user = get_current_user()
    return jsonify({
        'id': user['id'],
        'email': user['email']
    })
```

### Admin Route

```python
@api.route('/admin/users')
@require_role(['admin'])
def list_users():
    # Only admins can access
    users = get_all_users()
    return jsonify(users)
```

### Mixed Access Route

```python
@api.route('/content')
@optional_auth
def get_content():
    user = get_current_user()
    
    content = get_public_content()
    
    if user:
        # Add premium content for logged-in users
        content['premium'] = get_premium_content(user['id'])
    
    return jsonify(content)
```

---

## 🧪 Testing

### Mock Authentication

```python
from unittest.mock import patch

def test_protected_route(client):
    mock_user = {
        'id': 'test-user-id',
        'email': 'test@example.com',
        'role': 'user'
    }
    
    with patch('shared.auth.decorators.get_auth_provider') as mock:
        mock.return_value.verify_token.return_value = mock_user
        
        response = client.get('/api/protected', headers={
            'Authorization': 'Bearer fake-token'
        })
        
        assert response.status_code == 200
```

---

## 📚 Related Documentation

- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - Environment configuration
- [FRONTEND.md](FRONTEND.md) - Frontend auth components
