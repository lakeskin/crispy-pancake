# 🎨 Frontend Module

Reusable frontend components and patterns.

---

## 📦 Module Structure

```
frontend/
├── src/
│   ├── services/
│   │   ├── api.ts            # API client
│   │   └── authStorage.ts    # Token storage
│   ├── contexts/
│   │   └── AuthContext.tsx   # Auth context
│   ├── components/
│   │   ├── auth/
│   │   │   └── AuthModal.tsx # Login/signup modal
│   │   └── credits/
│   │       └── CreditPackagesModal.tsx
│   └── ThemeProvider.tsx     # Dynamic theming
└── package.json
```

---

## 🔐 Auth Storage

Token persistence with "Remember Me" functionality.

### Usage

```typescript
import { authStorage } from '../services/authStorage';

// After login - store session
authStorage.setSession(session, rememberMe, user);

// Get current tokens
const { accessToken, refreshToken, expiresAt } = authStorage.getTokens();

// Get stored user
const user = authStorage.getUser();

// Check if should refresh
if (authStorage.shouldRefreshToken()) {
    await refreshToken();
}

// Check if expired
if (authStorage.isTokenExpired()) {
    // Force re-login
}

// Logout
authStorage.clear();
```

### Configuration

```typescript
authStorage.configure({
    accessTokenKey: 'auth_token',
    refreshTokenKey: 'auth_refresh_token',
    userKey: 'auth_user',
    rememberMeKey: 'auth_remember_me',
    expiresAtKey: 'auth_expires_at',
    refreshThresholdSeconds: 300,  // 5 minutes
    defaultRememberMe: true,
});
```

---

## 🔄 Auth Context

React context for authentication state.

### Provider Setup

```tsx
// App.tsx
import { AuthProvider } from './contexts/AuthContext';

function App() {
    return (
        <AuthProvider>
            <YourApp />
        </AuthProvider>
    );
}
```

### Using the Hook

```tsx
import { useAuth } from '../contexts/AuthContext';

function MyComponent() {
    const {
        user,
        token,
        loading,
        isAuthenticated,
        login,
        logout,
        signup,
        refreshToken,
    } = useAuth();

    if (loading) return <Loading />;

    if (!isAuthenticated) {
        return <LoginPrompt />;
    }

    return <div>Hello, {user.email}!</div>;
}
```

### Auth Actions

```tsx
const { login, signup, logout } = useAuth();

// Login
try {
    await login(email, password, rememberMe);
    // User is now logged in
} catch (error) {
    // Handle error
}

// Signup
try {
    const result = await signup(email, password, name);
    if (result.email_confirmation_required) {
        // Show "check your email" message
    }
} catch (error) {
    // Handle error
}

// Logout
await logout();
```

---

## 🪟 Auth Modal

Pre-built login/signup modal.

### Usage

```tsx
import AuthModal from '../components/auth/AuthModal';

function Header() {
    const [authOpen, setAuthOpen] = useState(false);

    return (
        <>
            <Button onClick={() => setAuthOpen(true)}>
                Sign In
            </Button>
            
            <AuthModal
                open={authOpen}
                onClose={() => setAuthOpen(false)}
            />
        </>
    );
}
```

---

## 💳 Credit Packages Modal

Pre-built credit purchase modal.

### Usage

```tsx
import CreditPackagesModal from '../components/credits/CreditPackagesModal';

function PricingSection() {
    const [open, setOpen] = useState(false);

    return (
        <>
            <Button onClick={() => setOpen(true)}>
                Buy Credits
            </Button>
            
            <CreditPackagesModal
                open={open}
                onClose={() => setOpen(false)}
                onPurchaseComplete={() => {
                    // Refresh balance
                }}
            />
        </>
    );
}
```

---

## 🎨 Theme Provider

Dynamic theming with API-driven configuration.

### Setup

```tsx
import { ThemeProviderWrapper } from './ThemeProvider';

function App() {
    return (
        <ThemeProviderWrapper>
            <YourApp />
        </ThemeProviderWrapper>
    );
}
```

### Using Theme Config

```tsx
import { useThemeConfig } from './ThemeProvider';

function MyComponent() {
    const { config, updateConfig, refreshConfig } = useThemeConfig();

    return (
        <Button className={`btn-${config.customClasses.buttons.primary}`}>
            Themed Button
        </Button>
    );
}
```

### Custom Classes

The theme system supports custom classes for:
- **Buttons**: `btn-{name}`
- **Cards**: `card-{name}`
- **Typography**: `text-{name}`
- **Inputs**: `input-{name}`
- **Chips**: `chip-{name}`

```tsx
// Define in theme config
customClasses: {
    buttons: {
        primary: {
            backgroundColor: '#6200ea',
            color: '#ffffff',
            borderRadius: '12px',
        }
    }
}

// Use in components
<Button className="btn-primary">Click Me</Button>
```

---

## 📡 API Service

Centralized API client.

### Setup

```typescript
// services/api.ts
import axios from 'axios';
import { authStorage } from './authStorage';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
});

// Add auth token to requests
api.interceptors.request.use((config) => {
    const { accessToken } = authStorage.getTokens();
    if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
});

// Handle 401 responses
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Try to refresh token
            const refreshed = await refreshToken();
            if (refreshed) {
                // Retry original request
                return api.request(error.config);
            }
        }
        return Promise.reject(error);
    }
);

export default api;
```

### Making API Calls

```typescript
import api from '../services/api';

// GET request
const { data } = await api.get('/me');

// POST request
const { data } = await api.post('/generate', {
    prompt: 'A beautiful sunset'
});

// With error handling
try {
    const { data } = await api.post('/checkout', { package_id: 'creator' });
    window.location.href = data.checkout_url;
} catch (error) {
    if (error.response?.status === 402) {
        // Insufficient credits
    }
}
```

---

## 📱 Mobile Support

The frontend includes Capacitor configuration for mobile:

```typescript
// capacitor.config.ts
const config: CapacitorConfig = {
    appId: 'com.yourapp.app',
    appName: 'Your App',
    webDir: 'dist',
    server: {
        androidScheme: 'https'
    }
};
```

See `MOBILE_QUICK_START.md` for mobile deployment.

---

## 📚 Related Documentation

- [AUTH.md](AUTH.md) - Backend auth module
- [CREDITS.md](CREDITS.md) - Backend credit system
- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - Environment variables
