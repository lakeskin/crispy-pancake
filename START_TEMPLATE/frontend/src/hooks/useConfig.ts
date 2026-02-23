/**
 * useConfig Hook
 * ==============
 * React hook for managing configuration state with the admin API.
 * 
 * Usage:
 * ```tsx
 * function ConfigEditor() {
 *   const { data, loading, error, save, reload } = useConfig('backend');
 *   
 *   if (loading) return <Loading />;
 *   if (error) return <Error message={error} />;
 *   
 *   return (
 *     <Form
 *       data={data}
 *       onSave={async (newData) => {
 *         const result = await save(newData);
 *         if (result.success) showSuccess('Saved!');
 *       }}
 *     />
 *   );
 * }
 * ```
 */

import { useState, useEffect, useCallback } from 'react';
import { adminApi, type ConfigResponse, type SaveResponse } from '../services/adminApi';

export interface UseConfigResult<T = Record<string, unknown>> {
  /** Current config data */
  data: T | null;
  /** Whether config is loading */
  loading: boolean;
  /** Error message if load failed */
  error: string | null;
  /** Whether there are unsaved changes */
  isDirty: boolean;
  /** Config metadata (name, path, last_modified) */
  metadata: {
    name: string;
    path: string;
    lastModified: string | null;
  } | null;
  /** Reload config from server */
  reload: () => Promise<void>;
  /** Save config to server */
  save: (newData: T) => Promise<SaveResponse>;
  /** Update local data (marks as dirty) */
  setData: (data: T | ((prev: T | null) => T)) => void;
  /** Reset to last saved state */
  reset: () => void;
}

export function useConfig<T = Record<string, unknown>>(
  configId: string
): UseConfigResult<T> {
  const [data, setDataInternal] = useState<T | null>(null);
  const [savedData, setSavedData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<UseConfigResult['metadata']>(null);
  
  const isDirty = data !== savedData && JSON.stringify(data) !== JSON.stringify(savedData);
  
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await adminApi.getConfig<T>(configId);
      
      if (response.success && response.data) {
        setDataInternal(response.data);
        setSavedData(response.data);
        setMetadata({
          name: response.name || configId,
          path: response.path || '',
          lastModified: response.last_modified || null,
        });
      } else {
        setError(response.error || 'Failed to load config');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load config');
    } finally {
      setLoading(false);
    }
  }, [configId]);
  
  useEffect(() => {
    load();
  }, [load]);
  
  const save = async (newData: T): Promise<SaveResponse> => {
    try {
      const response = await adminApi.saveConfig(configId, newData as Record<string, unknown>);
      
      if (response.success) {
        setDataInternal(newData);
        setSavedData(newData);
      }
      
      return response;
    } catch (e) {
      return {
        success: false,
        error: e instanceof Error ? e.message : 'Failed to save config',
      };
    }
  };
  
  const setData = (newData: T | ((prev: T | null) => T)) => {
    if (typeof newData === 'function') {
      setDataInternal((prev) => (newData as (prev: T | null) => T)(prev));
    } else {
      setDataInternal(newData);
    }
  };
  
  const reset = () => {
    setDataInternal(savedData);
  };
  
  return {
    data,
    loading,
    error,
    isDirty,
    metadata,
    reload: load,
    save,
    setData,
    reset,
  };
}

/**
 * useConfigSection Hook
 * =====================
 * Hook for managing a specific section of a config using dot notation.
 * 
 * Usage:
 * ```tsx
 * const { data, save } = useConfigSection('backend', 'appearance.fonts');
 * ```
 */
export function useConfigSection<T = unknown>(
  configId: string,
  sectionPath: string
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await adminApi.getSection<T>(configId, sectionPath);
      
      if (response.success) {
        setData(response.data);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load section');
    } finally {
      setLoading(false);
    }
  }, [configId, sectionPath]);
  
  useEffect(() => {
    load();
  }, [load]);
  
  const save = async (newData: T): Promise<SaveResponse> => {
    try {
      const response = await adminApi.saveSection(configId, sectionPath, newData);
      
      if (response.success) {
        setData(newData);
      }
      
      return response;
    } catch (e) {
      return {
        success: false,
        error: e instanceof Error ? e.message : 'Failed to save section',
      };
    }
  };
  
  return {
    data,
    loading,
    error,
    reload: load,
    save,
    setData,
  };
}
