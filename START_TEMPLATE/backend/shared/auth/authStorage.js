/**
 * Auth Storage Utility
 * 
 * Shareable, reusable, and configurable authentication storage for frontend apps.
 * Handles token persistence with "Remember Me" functionality.
 * 
 * Features:
 * - Configurable storage (localStorage for remember me, sessionStorage otherwise)
 * - Automatic token refresh before expiry
 * - Secure token management
 * - Cross-tab synchronization
 * 
 * Usage:
 *   import { authStorage } from 'shared/auth/authStorage';
 *   
 *   // Store tokens after login
 *   authStorage.setSession(session, rememberMe);
 *   
 *   // Get current tokens
 *   const { accessToken, refreshToken } = authStorage.getTokens();
 *   
 *   // Check if token needs refresh
 *   if (authStorage.shouldRefreshToken()) {
 *     // Call refresh endpoint
 *   }
 */

// Default configuration (can be overridden)
const defaultConfig = {
  accessTokenKey: 'auth_token',
  refreshTokenKey: 'auth_refresh_token',
  userKey: 'auth_user',
  rememberMeKey: 'auth_remember_me',
  expiresAtKey: 'auth_expires_at',
  refreshThresholdSeconds: 300, // Refresh 5 minutes before expiry
  defaultRememberMe: true,
};

class AuthStorage {
  constructor(config = {}) {
    this.config = { ...defaultConfig, ...config };
    this._refreshCallbacks = [];
  }

  /**
   * Configure the auth storage
   * @param {Object} config - Configuration options
   */
  configure(config) {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get the appropriate storage based on remember me setting
   * @returns {Storage} localStorage or sessionStorage
   */
  _getStorage() {
    const rememberMe = localStorage.getItem(this.config.rememberMeKey) === 'true';
    return rememberMe ? localStorage : sessionStorage;
  }

  /**
   * Get the current remember me setting
   * @returns {boolean}
   */
  getRememberMe() {
    // Check localStorage first (it persists the preference)
    const stored = localStorage.getItem(this.config.rememberMeKey);
    if (stored !== null) {
      return stored === 'true';
    }
    return this.config.defaultRememberMe;
  }

  /**
   * Set the remember me preference
   * @param {boolean} rememberMe
   */
  setRememberMe(rememberMe) {
    localStorage.setItem(this.config.rememberMeKey, String(rememberMe));
  }

  /**
   * Store session data after login
   * @param {Object} session - Session object with access_token, refresh_token, expires_at/expires_in
   * @param {boolean} rememberMe - Whether to persist across browser sessions
   * @param {Object} user - Optional user data to store
   */
  setSession(session, rememberMe = true, user = null) {
    // Store remember me preference in localStorage (persists for future logins)
    this.setRememberMe(rememberMe);
    
    // Choose storage based on remember me
    const storage = rememberMe ? localStorage : sessionStorage;
    
    // Store access token
    if (session.access_token) {
      storage.setItem(this.config.accessTokenKey, session.access_token);
    }
    
    // Store refresh token
    if (session.refresh_token) {
      storage.setItem(this.config.refreshTokenKey, session.refresh_token);
    }
    
    // Store expiration time
    if (session.expires_at) {
      storage.setItem(this.config.expiresAtKey, String(session.expires_at));
    } else if (session.expires_in) {
      // Calculate expiration from expires_in (seconds from now)
      const expiresAt = Math.floor(Date.now() / 1000) + session.expires_in;
      storage.setItem(this.config.expiresAtKey, String(expiresAt));
    }
    
    // Store user data if provided
    if (user) {
      storage.setItem(this.config.userKey, JSON.stringify(user));
    }
    
    // Sync to other storage to prevent duplicates
    this._syncStorage(rememberMe);
  }

  /**
   * Update tokens after refresh
   * @param {Object} session - New session data
   */
  updateTokens(session) {
    const rememberMe = this.getRememberMe();
    const storage = rememberMe ? localStorage : sessionStorage;
    
    if (session.access_token) {
      storage.setItem(this.config.accessTokenKey, session.access_token);
    }
    
    if (session.refresh_token) {
      storage.setItem(this.config.refreshTokenKey, session.refresh_token);
    }
    
    if (session.expires_at) {
      storage.setItem(this.config.expiresAtKey, String(session.expires_at));
    } else if (session.expires_in) {
      const expiresAt = Math.floor(Date.now() / 1000) + session.expires_in;
      storage.setItem(this.config.expiresAtKey, String(expiresAt));
    }
    
    this._syncStorage(rememberMe);
  }

  /**
   * Get current tokens
   * @returns {Object} { accessToken, refreshToken, expiresAt }
   */
  getTokens() {
    // Try localStorage first (remember me), then sessionStorage
    let accessToken = localStorage.getItem(this.config.accessTokenKey);
    let refreshToken = localStorage.getItem(this.config.refreshTokenKey);
    let expiresAt = localStorage.getItem(this.config.expiresAtKey);
    
    // Fallback to sessionStorage
    if (!accessToken) {
      accessToken = sessionStorage.getItem(this.config.accessTokenKey);
      refreshToken = sessionStorage.getItem(this.config.refreshTokenKey);
      expiresAt = sessionStorage.getItem(this.config.expiresAtKey);
    }
    
    return {
      accessToken,
      refreshToken,
      expiresAt: expiresAt ? parseInt(expiresAt, 10) : null,
    };
  }

  /**
   * Get stored user data
   * @returns {Object|null} User data or null
   */
  getUser() {
    // Try localStorage first, then sessionStorage
    let userJson = localStorage.getItem(this.config.userKey);
    if (!userJson) {
      userJson = sessionStorage.getItem(this.config.userKey);
    }
    
    try {
      return userJson ? JSON.parse(userJson) : null;
    } catch {
      return null;
    }
  }

  /**
   * Store user data
   * @param {Object} user - User data to store
   */
  setUser(user) {
    const storage = this._getStorage();
    if (user) {
      storage.setItem(this.config.userKey, JSON.stringify(user));
    }
  }

  /**
   * Check if access token is expired or about to expire
   * @returns {boolean} True if token should be refreshed
   */
  shouldRefreshToken() {
    const { accessToken, refreshToken, expiresAt } = this.getTokens();
    
    // No token or no refresh token means can't refresh
    if (!accessToken || !refreshToken) {
      return false;
    }
    
    // No expiration info - assume needs refresh if we have refresh token
    if (!expiresAt) {
      return true;
    }
    
    // Check if within threshold
    const now = Math.floor(Date.now() / 1000);
    const threshold = this.config.refreshThresholdSeconds;
    
    return (expiresAt - now) <= threshold;
  }

  /**
   * Check if access token is completely expired
   * @returns {boolean} True if token is expired
   */
  isTokenExpired() {
    const { accessToken, expiresAt } = this.getTokens();
    
    if (!accessToken) {
      return true;
    }
    
    if (!expiresAt) {
      // Try to decode token to check expiry
      try {
        const payload = JSON.parse(atob(accessToken.split('.')[1]));
        if (payload.exp) {
          return Date.now() >= payload.exp * 1000;
        }
      } catch {
        // Can't decode, assume valid
        return false;
      }
    }
    
    const now = Math.floor(Date.now() / 1000);
    return expiresAt <= now;
  }

  /**
   * Check if user has a valid session (token exists and not expired)
   * @returns {boolean}
   */
  hasValidSession() {
    const { accessToken } = this.getTokens();
    return !!accessToken && !this.isTokenExpired();
  }

  /**
   * Check if we can attempt to refresh (have refresh token)
   * @returns {boolean}
   */
  canRefresh() {
    const { refreshToken } = this.getTokens();
    return !!refreshToken;
  }

  /**
   * Clear all auth data (logout)
   */
  clear() {
    // Clear from both storages
    const keys = [
      this.config.accessTokenKey,
      this.config.refreshTokenKey,
      this.config.userKey,
      this.config.expiresAtKey,
    ];
    
    keys.forEach(key => {
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
    });
    
    // Optionally keep remember me preference
    // localStorage.removeItem(this.config.rememberMeKey);
  }

  /**
   * Sync storage to prevent duplicates across localStorage and sessionStorage
   * @param {boolean} rememberMe - Which storage to keep
   */
  _syncStorage(rememberMe) {
    const keys = [
      this.config.accessTokenKey,
      this.config.refreshTokenKey,
      this.config.userKey,
      this.config.expiresAtKey,
    ];
    
    // Clear the storage we're NOT using
    const clearStorage = rememberMe ? sessionStorage : localStorage;
    keys.forEach(key => {
      clearStorage.removeItem(key);
    });
  }

  /**
   * Register a callback for when token refresh is needed
   * @param {Function} callback - Function to call when refresh is needed
   * @returns {Function} Unsubscribe function
   */
  onRefreshNeeded(callback) {
    this._refreshCallbacks.push(callback);
    return () => {
      this._refreshCallbacks = this._refreshCallbacks.filter(cb => cb !== callback);
    };
  }

  /**
   * Start automatic token refresh monitoring
   * @param {Function} refreshFn - Async function that performs the refresh
   * @param {number} checkInterval - How often to check (ms), default 30 seconds
   * @returns {Function} Stop function
   */
  startAutoRefresh(refreshFn, checkInterval = 30000) {
    let isRefreshing = false;
    
    const check = async () => {
      if (isRefreshing) return;
      
      if (this.shouldRefreshToken()) {
        isRefreshing = true;
        try {
          await refreshFn();
          console.log('[AuthStorage] Token refreshed automatically');
        } catch (error) {
          console.error('[AuthStorage] Auto-refresh failed:', error);
          // Notify callbacks
          this._refreshCallbacks.forEach(cb => cb(error));
        } finally {
          isRefreshing = false;
        }
      }
    };
    
    // Check immediately
    check();
    
    // Set up interval
    const intervalId = setInterval(check, checkInterval);
    
    // Return stop function
    return () => clearInterval(intervalId);
  }
}

// Export singleton instance
export const authStorage = new AuthStorage();

// Export class for custom instances
export default AuthStorage;
