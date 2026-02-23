/**
 * Auth Storage Utility
 * 
 * Shareable, reusable, and configurable authentication storage for frontend apps.
 * Handles token persistence with "Remember Me" functionality.
 */

interface AuthStorageConfig {
  accessTokenKey: string;
  refreshTokenKey: string;
  userKey: string;
  rememberMeKey: string;
  expiresAtKey: string;
  refreshThresholdSeconds: number;
  defaultRememberMe: boolean;
}

interface Session {
  access_token?: string;
  refresh_token?: string;
  expires_at?: number;
  expires_in?: number;
}

interface Tokens {
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
}

interface User {
  id: string;
  email: string;
  [key: string]: unknown;
}

const defaultConfig: AuthStorageConfig = {
  accessTokenKey: 'auth_token',
  refreshTokenKey: 'auth_refresh_token',
  userKey: 'auth_user',
  rememberMeKey: 'auth_remember_me',
  expiresAtKey: 'auth_expires_at',
  refreshThresholdSeconds: 300,
  defaultRememberMe: true,
};

class AuthStorage {
  private config: AuthStorageConfig;
  private _refreshCallbacks: ((error?: Error) => void)[];

  constructor(config: Partial<AuthStorageConfig> = {}) {
    this.config = { ...defaultConfig, ...config };
    this._refreshCallbacks = [];
  }

  configure(config: Partial<AuthStorageConfig>): void {
    this.config = { ...this.config, ...config };
  }

  private _getStorage(): Storage {
    const rememberMe = localStorage.getItem(this.config.rememberMeKey) === 'true';
    return rememberMe ? localStorage : sessionStorage;
  }

  getRememberMe(): boolean {
    const stored = localStorage.getItem(this.config.rememberMeKey);
    if (stored !== null) {
      return stored === 'true';
    }
    return this.config.defaultRememberMe;
  }

  setRememberMe(rememberMe: boolean): void {
    localStorage.setItem(this.config.rememberMeKey, String(rememberMe));
  }

  setSession(session: Session, rememberMe = true, user: User | null = null): void {
    this.setRememberMe(rememberMe);
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

    if (user) {
      storage.setItem(this.config.userKey, JSON.stringify(user));
    }

    this._syncStorage(rememberMe);
  }

  updateTokens(session: Session): void {
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

  getTokens(): Tokens {
    let accessToken = localStorage.getItem(this.config.accessTokenKey);
    let refreshToken = localStorage.getItem(this.config.refreshTokenKey);
    let expiresAt = localStorage.getItem(this.config.expiresAtKey);

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

  getUser(): User | null {
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

  setUser(user: User): void {
    const storage = this._getStorage();
    if (user) {
      storage.setItem(this.config.userKey, JSON.stringify(user));
    }
  }

  shouldRefreshToken(): boolean {
    const { accessToken, refreshToken, expiresAt } = this.getTokens();

    if (!accessToken || !refreshToken) {
      return false;
    }

    if (!expiresAt) {
      return true;
    }

    const now = Math.floor(Date.now() / 1000);
    const threshold = this.config.refreshThresholdSeconds;

    return expiresAt - now <= threshold;
  }

  isTokenExpired(): boolean {
    const { accessToken, expiresAt } = this.getTokens();

    if (!accessToken) {
      return true;
    }

    if (!expiresAt) {
      try {
        const payload = JSON.parse(atob(accessToken.split('.')[1]));
        if (payload.exp) {
          return Date.now() >= payload.exp * 1000;
        }
      } catch {
        return false;
      }
    }

    const now = Math.floor(Date.now() / 1000);
    return expiresAt ? expiresAt <= now : false;
  }

  hasValidSession(): boolean {
    const { accessToken } = this.getTokens();
    return !!accessToken && !this.isTokenExpired();
  }

  canRefresh(): boolean {
    const { refreshToken } = this.getTokens();
    return !!refreshToken;
  }

  clear(): void {
    const keys = [
      this.config.accessTokenKey,
      this.config.refreshTokenKey,
      this.config.userKey,
      this.config.expiresAtKey,
    ];

    keys.forEach((key) => {
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
    });
  }

  private _syncStorage(rememberMe: boolean): void {
    const keys = [
      this.config.accessTokenKey,
      this.config.refreshTokenKey,
      this.config.userKey,
      this.config.expiresAtKey,
    ];

    const clearStorage = rememberMe ? sessionStorage : localStorage;
    keys.forEach((key) => {
      clearStorage.removeItem(key);
    });
  }

  onRefreshNeeded(callback: (error?: Error) => void): () => void {
    this._refreshCallbacks.push(callback);
    return () => {
      this._refreshCallbacks = this._refreshCallbacks.filter((cb) => cb !== callback);
    };
  }

  startAutoRefresh(refreshFn: () => Promise<void>, checkInterval = 30000): () => void {
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
          this._refreshCallbacks.forEach((cb) => cb(error as Error));
        } finally {
          isRefreshing = false;
        }
      }
    };

    check();
    const intervalId = setInterval(check, checkInterval);

    return () => clearInterval(intervalId);
  }
}

export const authStorage = new AuthStorage();
export default AuthStorage;
