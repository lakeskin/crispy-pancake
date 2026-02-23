/**
 * ConfigEditor Component
 * ======================
 * Generic form-based editor for YAML/JSON configuration sections.
 * Automatically generates form fields based on config structure.
 * 
 * Usage:
 * ```tsx
 * <ConfigEditor
 *   configId="backend"
 *   sectionPath="appearance.fonts"
 *   title="Font Settings"
 *   onSave={(result) => console.log('Saved:', result)}
 * />
 * ```
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Switch,
  FormControlLabel,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Stack,
  Alert,
  CircularProgress,
  Divider,
  IconButton,
  Tooltip,
  Collapse,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import RefreshIcon from '@mui/icons-material/Refresh';
import UndoIcon from '@mui/icons-material/Undo';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';

import { useConfig, useConfigSection } from '../../hooks/useConfig';
import type { SaveResponse } from '../../services/adminApi';

// =============================================================================
// Types
// =============================================================================

interface FieldConfig {
  type?: 'text' | 'number' | 'boolean' | 'select' | 'color' | 'json';
  label?: string;
  description?: string;
  options?: Array<{ value: string | number; label: string }>;
  min?: number;
  max?: number;
  step?: number;
  multiline?: boolean;
  rows?: number;
}

interface ConfigEditorProps {
  /** Config ID (e.g., 'backend', 'theme') */
  configId: string;
  /** Optional section path using dot notation (e.g., 'appearance.fonts') */
  sectionPath?: string;
  /** Title for the editor */
  title?: string;
  /** Description text */
  description?: string;
  /** Field configurations for customizing form fields */
  fieldConfig?: Record<string, FieldConfig>;
  /** Fields to exclude from the form */
  excludeFields?: string[];
  /** Callback after successful save */
  onSave?: (result: SaveResponse) => void;
  /** Callback on error */
  onError?: (error: string) => void;
  /** Whether to show the reload button */
  showReload?: boolean;
  /** Whether to show the reset button */
  showReset?: boolean;
  /** Custom save button text */
  saveButtonText?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

function inferFieldType(value: unknown): FieldConfig['type'] {
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return 'number';
  if (typeof value === 'object') return 'json';
  if (typeof value === 'string') {
    if (value.startsWith('#') && (value.length === 4 || value.length === 7)) {
      return 'color';
    }
  }
  return 'text';
}

function formatLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (str) => str.toUpperCase())
    .trim();
}

// =============================================================================
// Field Renderer
// =============================================================================

interface FieldProps {
  fieldKey: string;
  value: unknown;
  config: FieldConfig;
  onChange: (key: string, value: unknown) => void;
  disabled?: boolean;
}

function Field({ fieldKey, value, config, onChange, disabled }: FieldProps) {
  const type = config.type || inferFieldType(value);
  const label = config.label || formatLabel(fieldKey);
  
  switch (type) {
    case 'boolean':
      return (
        <FormControlLabel
          control={
            <Switch
              checked={Boolean(value)}
              onChange={(e) => onChange(fieldKey, e.target.checked)}
              disabled={disabled}
            />
          }
          label={label}
        />
      );
    
    case 'number':
      return (
        <TextField
          fullWidth
          type="number"
          label={label}
          value={value ?? ''}
          onChange={(e) => onChange(fieldKey, Number(e.target.value))}
          disabled={disabled}
          helperText={config.description}
          inputProps={{
            min: config.min,
            max: config.max,
            step: config.step || 1,
          }}
        />
      );
    
    case 'select':
      return (
        <FormControl fullWidth>
          <InputLabel>{label}</InputLabel>
          <Select
            value={value ?? ''}
            label={label}
            onChange={(e) => onChange(fieldKey, e.target.value)}
            disabled={disabled}
          >
            {config.options?.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>
                {opt.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    
    case 'color':
      return (
        <TextField
          fullWidth
          type="color"
          label={label}
          value={value ?? '#000000'}
          onChange={(e) => onChange(fieldKey, e.target.value)}
          disabled={disabled}
          helperText={config.description}
          InputProps={{
            sx: { height: 56 },
          }}
        />
      );
    
    case 'json':
      return (
        <TextField
          fullWidth
          multiline
          rows={4}
          label={label}
          value={typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
          onChange={(e) => {
            try {
              onChange(fieldKey, JSON.parse(e.target.value));
            } catch {
              // Keep as string if invalid JSON
            }
          }}
          disabled={disabled}
          helperText={config.description || 'JSON format'}
          sx={{
            '& .MuiInputBase-input': {
              fontFamily: 'monospace',
              fontSize: '0.875rem',
            },
          }}
        />
      );
    
    default: // text
      return (
        <TextField
          fullWidth
          multiline={config.multiline}
          rows={config.rows || (config.multiline ? 3 : 1)}
          label={label}
          value={value ?? ''}
          onChange={(e) => onChange(fieldKey, e.target.value)}
          disabled={disabled}
          helperText={config.description}
        />
      );
  }
}

// =============================================================================
// Main Component
// =============================================================================

export default function ConfigEditor({
  configId,
  sectionPath,
  title,
  description,
  fieldConfig = {},
  excludeFields = [],
  onSave,
  onError,
  showReload = true,
  showReset = true,
  saveButtonText = 'Save Changes',
}: ConfigEditorProps) {
  // Use section hook if path provided, otherwise full config
  const fullConfig = useConfig(configId);
  const sectionConfig = useConfigSection(configId, sectionPath || '');
  
  const hook = sectionPath ? sectionConfig : fullConfig;
  const { data, loading, error, reload, save } = hook;
  const isDirty = 'isDirty' in hook ? hook.isDirty : false;
  const reset = 'reset' in hook ? hook.reset : () => reload();
  
  const [localData, setLocalData] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  
  // Sync local data with loaded data
  useEffect(() => {
    if (data && typeof data === 'object') {
      setLocalData(data as Record<string, unknown>);
    }
  }, [data]);
  
  const handleFieldChange = (key: string, value: unknown) => {
    setLocalData((prev) => ({
      ...prev,
      [key]: value,
    }));
    setSaveError(null);
    setSaveSuccess(false);
  };
  
  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    
    try {
      const result = await save(localData);
      
      if (result.success) {
        setSaveSuccess(true);
        onSave?.(result);
        setTimeout(() => setSaveSuccess(false), 3000);
      } else {
        setSaveError(result.error || 'Failed to save');
        onError?.(result.error || 'Failed to save');
      }
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Failed to save';
      setSaveError(errorMsg);
      onError?.(errorMsg);
    } finally {
      setSaving(false);
    }
  };
  
  const handleReset = () => {
    if (data && typeof data === 'object') {
      setLocalData(data as Record<string, unknown>);
    }
    setSaveError(null);
    setSaveSuccess(false);
  };
  
  const toggleSection = (key: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };
  
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }
  
  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
        <Button size="small" onClick={reload} sx={{ ml: 2 }}>
          Retry
        </Button>
      </Alert>
    );
  }
  
  // Filter and organize fields
  const fields = Object.entries(localData).filter(
    ([key]) => !excludeFields.includes(key)
  );
  
  const simpleFields = fields.filter(([, value]) => typeof value !== 'object' || value === null);
  const objectFields = fields.filter(([, value]) => typeof value === 'object' && value !== null);
  
  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h6">{title || `${configId} Configuration`}</Typography>
          {description && (
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
          )}
        </Box>
        <Stack direction="row" spacing={1}>
          {showReload && (
            <Tooltip title="Reload">
              <IconButton onClick={reload} disabled={saving}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          )}
          {showReset && (
            <Tooltip title="Reset Changes">
              <IconButton onClick={handleReset} disabled={saving}>
                <UndoIcon />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      </Stack>
      
      {/* Alerts */}
      {saveError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setSaveError(null)}>
          {saveError}
        </Alert>
      )}
      {saveSuccess && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Configuration saved successfully!
        </Alert>
      )}
      
      <Divider sx={{ mb: 3 }} />
      
      {/* Simple Fields */}
      <Stack spacing={2}>
        {simpleFields.map(([key, value]) => (
          <Field
            key={key}
            fieldKey={key}
            value={value}
            config={fieldConfig[key] || {}}
            onChange={handleFieldChange}
            disabled={saving}
          />
        ))}
      </Stack>
      
      {/* Nested Object Fields */}
      {objectFields.length > 0 && (
        <Box sx={{ mt: 3 }}>
          {objectFields.map(([key, value]) => (
            <Box key={key} sx={{ mb: 2 }}>
              <Button
                fullWidth
                onClick={() => toggleSection(key)}
                endIcon={expandedSections.has(key) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                sx={{
                  justifyContent: 'space-between',
                  textTransform: 'none',
                  bgcolor: 'action.hover',
                  mb: 1,
                }}
              >
                <Typography variant="subtitle2">{formatLabel(key)}</Typography>
              </Button>
              <Collapse in={expandedSections.has(key)}>
                <Box sx={{ pl: 2, borderLeft: 2, borderColor: 'divider' }}>
                  <TextField
                    fullWidth
                    multiline
                    rows={6}
                    value={JSON.stringify(value, null, 2)}
                    onChange={(e) => {
                      try {
                        handleFieldChange(key, JSON.parse(e.target.value));
                      } catch {
                        // Invalid JSON, keep current
                      }
                    }}
                    disabled={saving}
                    sx={{
                      '& .MuiInputBase-input': {
                        fontFamily: 'monospace',
                        fontSize: '0.875rem',
                      },
                    }}
                  />
                </Box>
              </Collapse>
            </Box>
          ))}
        </Box>
      )}
      
      {/* Save Button */}
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : saveButtonText}
        </Button>
      </Box>
    </Paper>
  );
}
