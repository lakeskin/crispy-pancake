/**
 * BackupManager Component
 * =======================
 * UI for listing, restoring, and managing config backups.
 * 
 * Usage:
 * ```tsx
 * <BackupManager
 *   configId="backend"
 *   onRestore={() => refetchConfig()}
 * />
 * ```
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Button,
  Stack,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Tooltip,
  Divider,
  TextField,
} from '@mui/material';
import RestoreIcon from '@mui/icons-material/SettingsBackupRestore';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import CleaningServicesIcon from '@mui/icons-material/CleaningServices';
import HistoryIcon from '@mui/icons-material/History';

import { adminApi, type BackupItem } from '../../services/adminApi';

// =============================================================================
// Types
// =============================================================================

interface BackupManagerProps {
  /** Optional: filter backups for specific config */
  configId?: string;
  /** Max backups to display */
  limit?: number;
  /** Callback after successful restore */
  onRestore?: () => void;
  /** Title override */
  title?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString();
}

function timeAgo(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;
  return formatDate(isoString);
}

// =============================================================================
// Main Component
// =============================================================================

export default function BackupManager({
  configId,
  limit = 20,
  onRestore,
  title = 'Configuration Backups',
}: BackupManagerProps) {
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  
  // Dialogs
  const [restoreDialog, setRestoreDialog] = useState<BackupItem | null>(null);
  const [cleanupDialog, setCleanupDialog] = useState(false);
  const [cleanupCount, setCleanupCount] = useState(10);
  const [targetConfigId, setTargetConfigId] = useState(configId || '');
  
  // Success/error messages
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Load backups
  const loadBackups = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await adminApi.listBackups(configId, limit);
      if (response.success) {
        setBackups(response.backups);
      } else {
        setError('Failed to load backups');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load backups');
    } finally {
      setLoading(false);
    }
  }, [configId, limit]);
  
  useEffect(() => {
    loadBackups();
  }, [loadBackups]);
  
  // Restore backup
  const handleRestore = async () => {
    if (!restoreDialog || !targetConfigId) return;
    
    setActionLoading(restoreDialog.filename);
    
    try {
      const response = await adminApi.restoreBackup(restoreDialog.filename, targetConfigId);
      
      if (response.success) {
        setSuccessMessage(`Restored ${restoreDialog.filename} successfully`);
        setRestoreDialog(null);
        onRestore?.();
        loadBackups();
        setTimeout(() => setSuccessMessage(null), 5000);
      } else {
        setError('Failed to restore backup');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to restore backup');
    } finally {
      setActionLoading(null);
    }
  };
  
  // Delete backup
  const handleDelete = async (backup: BackupItem) => {
    if (!confirm(`Delete backup "${backup.filename}"?`)) return;
    
    setActionLoading(backup.filename);
    
    try {
      const response = await adminApi.deleteBackup(backup.filename);
      
      if (response.success) {
        setSuccessMessage(`Deleted ${backup.filename}`);
        loadBackups();
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete backup');
    } finally {
      setActionLoading(null);
    }
  };
  
  // Cleanup old backups
  const handleCleanup = async () => {
    setActionLoading('cleanup');
    
    try {
      const response = await adminApi.cleanupBackups(cleanupCount, configId);
      
      if (response.success) {
        setSuccessMessage(`Cleaned up ${response.deleted_count} old backups`);
        setCleanupDialog(false);
        loadBackups();
        setTimeout(() => setSuccessMessage(null), 5000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Cleanup failed');
    } finally {
      setActionLoading(null);
    }
  };
  
  // Group backups by config
  const groupedBackups = backups.reduce((acc, backup) => {
    const key = backup.config_name || 'unknown';
    if (!acc[key]) acc[key] = [];
    acc[key].push(backup);
    return acc;
  }, {} as Record<string, BackupItem[]>);
  
  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <HistoryIcon color="primary" />
          <Typography variant="h6">{title}</Typography>
          <Chip label={`${backups.length} backups`} size="small" />
        </Stack>
        <Stack direction="row" spacing={1}>
          <Tooltip title="Cleanup old backups">
            <IconButton onClick={() => setCleanupDialog(true)}>
              <CleaningServicesIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Refresh">
            <IconButton onClick={loadBackups} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Stack>
      
      {/* Messages */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      )}
      
      {/* Loading */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}
      
      {/* Empty state */}
      {!loading && backups.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography color="text.secondary">No backups found</Typography>
        </Box>
      )}
      
      {/* Backup list */}
      {!loading && backups.length > 0 && (
        <Box>
          {Object.entries(groupedBackups).map(([configName, items]) => (
            <Box key={configName} sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                {configName.toUpperCase()}
              </Typography>
              <List dense>
                {items.map((backup) => (
                  <ListItem
                    key={backup.filename}
                    sx={{
                      bgcolor: 'background.default',
                      borderRadius: 1,
                      mb: 0.5,
                    }}
                  >
                    <ListItemText
                      primary={backup.filename}
                      secondary={
                        <Stack direction="row" spacing={2} component="span">
                          <span>{timeAgo(backup.created)}</span>
                          <span>{formatBytes(backup.size)}</span>
                        </Stack>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Tooltip title="Restore this backup">
                        <IconButton
                          edge="end"
                          onClick={() => {
                            setRestoreDialog(backup);
                            setTargetConfigId(backup.config_name || configId || '');
                          }}
                          disabled={actionLoading === backup.filename}
                        >
                          {actionLoading === backup.filename ? (
                            <CircularProgress size={20} />
                          ) : (
                            <RestoreIcon />
                          )}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete backup">
                        <IconButton
                          edge="end"
                          onClick={() => handleDelete(backup)}
                          disabled={actionLoading === backup.filename}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </Box>
          ))}
        </Box>
      )}
      
      {/* Restore Dialog */}
      <Dialog open={!!restoreDialog} onClose={() => setRestoreDialog(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Restore Backup</DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 2 }}>
            Restore <strong>{restoreDialog?.filename}</strong> to:
          </Typography>
          <TextField
            fullWidth
            label="Target Config ID"
            value={targetConfigId}
            onChange={(e) => setTargetConfigId(e.target.value)}
            helperText="The config ID to restore this backup to (e.g., 'backend', 'theme')"
          />
          <Alert severity="warning" sx={{ mt: 2 }}>
            The current configuration will be backed up before restoring.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRestoreDialog(null)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleRestore}
            disabled={!targetConfigId || actionLoading === restoreDialog?.filename}
            startIcon={actionLoading ? <CircularProgress size={16} /> : <RestoreIcon />}
          >
            Restore
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Cleanup Dialog */}
      <Dialog open={cleanupDialog} onClose={() => setCleanupDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Cleanup Old Backups</DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 2 }}>
            Delete old backups, keeping the most recent ones.
          </Typography>
          <TextField
            fullWidth
            type="number"
            label="Keep most recent"
            value={cleanupCount}
            onChange={(e) => setCleanupCount(Number(e.target.value))}
            inputProps={{ min: 1, max: 100 }}
            helperText="Number of most recent backups to keep per config"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCleanupDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="warning"
            onClick={handleCleanup}
            disabled={actionLoading === 'cleanup'}
            startIcon={actionLoading === 'cleanup' ? <CircularProgress size={16} /> : <CleaningServicesIcon />}
          >
            Cleanup
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
