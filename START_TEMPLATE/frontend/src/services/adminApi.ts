/**
 * Admin API Service
 * =================
 * Generic API client for the shared admin configuration endpoints.
 * Works with any backend using the shared/admin router factory.
 * 
 * Usage:
 * ```typescript
 * import { createAdminApi } from './adminApi';
 * 
 * const adminApi = createAdminApi('/api/admin');
 * const configs = await adminApi.listConfigs();
 * ```
 */

// =============================================================================
// Types
// =============================================================================

export interface ConfigListItem {
  id: string;
  name: string;
  description: string;
  category: string;
  path: string;
  exists: boolean;
  size: number;
  last_modified: string | null;
  format: string | null;
}

export interface ConfigResponse<T = Record<string, unknown>> {
  success: boolean;
  config_id?: string;
  name?: string;
  data?: T;
  path?: string;
  last_modified?: string;
  error?: string;
}

export interface SaveResponse {
  success: boolean;
  message?: string;
  backup_path?: string | null;
  error?: string;
}

export interface SearchMatch {
  path: string;
  type: 'key' | 'value';
  match: string;
}

export interface SearchResult {
  config_id: string;
  config_name: string;
  matches: SearchMatch[];
}

export interface SearchResponse {
  success: boolean;
  query: string;
  results: SearchResult[];
  total_matches: number;
}

export interface BackupItem {
  filename: string;
  path: string;
  size: number;
  created: string;
  config_name: string | null;
}

export interface BackupListResponse {
  success: boolean;
  backups: BackupItem[];
  total: number;
}

// =============================================================================
// API Factory
// =============================================================================

export interface AdminApi {
  // Config operations
  listConfigs(): Promise<{ success: boolean; configs: ConfigListItem[] }>;
  getConfig<T = Record<string, unknown>>(configId: string): Promise<ConfigResponse<T>>;
  saveConfig(configId: string, data: Record<string, unknown>): Promise<SaveResponse>;
  getSection<T = unknown>(configId: string, path: string): Promise<{ success: boolean; data: T }>;
  saveSection(configId: string, path: string, data: unknown): Promise<SaveResponse>;
  searchConfigs(query: string, caseSensitive?: boolean): Promise<SearchResponse>;
  reloadConfigs(): Promise<{ success: boolean; reloaded: string[]; errors: Array<{ config: string; error: string }> }>;
  
  // Backup operations
  listBackups(configName?: string, limit?: number): Promise<BackupListResponse>;
  restoreBackup(filename: string, configId: string): Promise<{ success: boolean; message: string; previous_backup?: string }>;
  deleteBackup(filename: string): Promise<{ success: boolean; message: string }>;
  cleanupBackups(keepCount?: number, configName?: string): Promise<{ success: boolean; deleted_count: number; deleted: string[] }>;
}

/**
 * Create an admin API client for the given base URL.
 * 
 * @param baseUrl - Base URL for admin endpoints (e.g., '/api/admin')
 * @param fetchOptions - Additional fetch options (e.g., for auth headers)
 */
export function createAdminApi(
  baseUrl: string = '/api/admin',
  fetchOptions: RequestInit = {}
): AdminApi {
  
  async function fetchAPI<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      ...fetchOptions,
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
        ...options.headers,
      },
    });
    
    const data = await response.json();
    
    if (!response.ok && !data.success) {
      throw new Error(data.error || data.detail || `API error: ${response.status}`);
    }
    
    return data;
  }
  
  return {
    // =========================================================================
    // Config Operations
    // =========================================================================
    
    async listConfigs() {
      return fetchAPI('/configs');
    },
    
    async getConfig<T = Record<string, unknown>>(configId: string) {
      return fetchAPI<ConfigResponse<T>>(`/configs/${configId}`);
    },
    
    async saveConfig(configId: string, data: Record<string, unknown>) {
      return fetchAPI<SaveResponse>(`/configs/${configId}`, {
        method: 'PUT',
        body: JSON.stringify({ data }),
      });
    },
    
    async getSection<T = unknown>(configId: string, path: string) {
      return fetchAPI<{ success: boolean; data: T }>(`/configs/${configId}/${path}`);
    },
    
    async saveSection(configId: string, path: string, data: unknown) {
      return fetchAPI<SaveResponse>(`/configs/${configId}/${path}`, {
        method: 'PUT',
        body: JSON.stringify({ data }),
      });
    },
    
    async searchConfigs(query: string, caseSensitive = false) {
      const params = new URLSearchParams({ q: query });
      if (caseSensitive) params.set('case_sensitive', 'true');
      return fetchAPI<SearchResponse>(`/configs/search?${params}`);
    },
    
    async reloadConfigs() {
      return fetchAPI('/configs/reload', { method: 'POST' });
    },
    
    // =========================================================================
    // Backup Operations
    // =========================================================================
    
    async listBackups(configName?: string, limit = 50) {
      const params = new URLSearchParams();
      if (configName) params.set('config_name', configName);
      if (limit) params.set('limit', String(limit));
      return fetchAPI<BackupListResponse>(`/backups?${params}`);
    },
    
    async restoreBackup(filename: string, configId: string) {
      return fetchAPI(`/backups/${filename}/restore?config_id=${configId}`, {
        method: 'POST',
      });
    },
    
    async deleteBackup(filename: string) {
      return fetchAPI(`/backups/${filename}`, { method: 'DELETE' });
    },
    
    async cleanupBackups(keepCount = 10, configName?: string) {
      return fetchAPI('/backups/cleanup', {
        method: 'POST',
        body: JSON.stringify({
          keep_count: keepCount,
          config_name: configName,
        }),
      });
    },
  };
}

// =============================================================================
// Default Export
// =============================================================================

// Default instance using standard base URL
export const adminApi = createAdminApi('/api/admin');
