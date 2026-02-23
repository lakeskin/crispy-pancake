/**
 * Admin Components Index
 * ======================
 * Export all admin panel components.
 */

export { default as ConfigEditor } from './ConfigEditor';
export { default as BackupManager } from './BackupManager';

// Re-export hooks and API for convenience
export { useConfig, useConfigSection } from '../../hooks/useConfig';
export { adminApi, createAdminApi } from '../../services/adminApi';
export type {
  ConfigListItem,
  ConfigResponse,
  SaveResponse,
  SearchResult,
  BackupItem,
} from '../../services/adminApi';
