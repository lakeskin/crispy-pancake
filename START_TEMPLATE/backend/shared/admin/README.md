# Admin Module

Reusable configuration management system for admin panels.

## Features

- **YAML/JSON Support**: Load and save both formats with automatic detection
- **Dot-Notation Access**: Get/set nested values like `appearance.fonts.heading`
- **Automatic Backups**: Every save creates a timestamped backup
- **FastAPI Integration**: One-line router creation with full CRUD endpoints
- **Search**: Find values across all config files
- **Hot-Reload**: Trigger config reloads without restart

## Quick Start

### Backend Setup

```python
from fastapi import FastAPI, Depends
from shared.admin import create_admin_router
from shared.auth.decorators import require_admin

# Define your configuration files
CONFIG_DEFINITIONS = {
    'backend': {
        'path': 'config.yaml',
        'name': 'Backend Config',
        'description': 'Main application settings',
        'category': 'core'
    },
    'theme': {
        'path': 'theme.json',
        'name': 'Theme Settings',
        'description': 'UI appearance configuration',
        'category': 'ui'
    },
    'credits': {
        'path': 'shared/credits/config.yaml',
        'name': 'Credits & Pricing',
        'description': 'Pricing packages and credit costs',
        'category': 'business'
    }
}

# Create the admin router
admin_router = create_admin_router(
    config_definitions=CONFIG_DEFINITIONS,
    require_admin=require_admin,  # Your auth dependency
    prefix="/api/admin",
    backup_dir="./config_backups"
)

# Add to your app
app = FastAPI()
app.include_router(admin_router)
```

### Using ConfigManager Directly

```python
from shared.admin import ConfigManager

manager = ConfigManager()

# Load a config
config = manager.load('config.yaml')

# Get nested value (returns None if not found)
font = manager.get_value(config, 'appearance.fonts.heading')

# Get with default
timeout = manager.get_value(config, 'api.timeout', default=30)

# Get strict (raises if not found)
try:
    font = manager.get_value_strict(config, 'appearance.fonts.heading')
except SectionNotFoundError:
    print("Font config not found")

# Set nested value (creates parents if needed)
config = manager.set_value(config, 'appearance.fonts.heading', 'Inter')

# Save with backup
backup_path = manager.save('config.yaml', config, create_backup=True)
print(f"Backup created: {backup_path}")

# Search across config
matches = manager.search(config, 'font')
for match in matches:
    print(f"{match['type']}: {match['path']} = {match['match']}")
```

### Using BackupManager

```python
from shared.admin import BackupManager

backups = BackupManager(backup_dir='./config_backups')

# List all backups
for backup in backups.list_backups():
    print(f"{backup['filename']} - {backup['created']}")

# List backups for specific config
theme_backups = backups.list_backups(config_name='theme')

# Restore a backup
previous = backups.restore(
    'theme_20240115_103045.json',
    target_path='theme.json',
    create_current_backup=True  # Backup current before restore
)

# Cleanup old backups (keep last 10 per config)
deleted = backups.cleanup(keep_count=10)
print(f"Deleted {len(deleted)} old backups")
```

## Generated API Endpoints

When you use `create_admin_router()`, you get these endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/configs` | List all configuration files |
| GET | `/api/admin/configs/{id}` | Get full config contents |
| PUT | `/api/admin/configs/{id}` | Save full config |
| GET | `/api/admin/configs/{id}/{path}` | Get section (dot notation) |
| PUT | `/api/admin/configs/{id}/{path}` | Save section |
| GET | `/api/admin/configs/search?q=query` | Search all configs |
| POST | `/api/admin/configs/reload` | Hot-reload configs |
| GET | `/api/admin/backups` | List all backups |
| POST | `/api/admin/backups/{file}/restore` | Restore backup |
| DELETE | `/api/admin/backups/{file}` | Delete backup |
| POST | `/api/admin/backups/cleanup` | Clean old backups |

## Frontend Integration

### API Client

```typescript
// services/adminApi.ts
const API_BASE = '/api/admin';

export async function listConfigs() {
  const res = await fetch(`${API_BASE}/configs`);
  return res.json();
}

export async function getConfig(configId: string) {
  const res = await fetch(`${API_BASE}/configs/${configId}`);
  return res.json();
}

export async function saveConfig(configId: string, data: any) {
  const res = await fetch(`${API_BASE}/configs/${configId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data })
  });
  return res.json();
}

export async function getSection(configId: string, path: string) {
  const res = await fetch(`${API_BASE}/configs/${configId}/${path}`);
  return res.json();
}

export async function saveSection(configId: string, path: string, data: any) {
  const res = await fetch(`${API_BASE}/configs/${configId}/${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data })
  });
  return res.json();
}

export async function searchConfigs(query: string) {
  const res = await fetch(`${API_BASE}/configs/search?q=${encodeURIComponent(query)}`);
  return res.json();
}
```

### React Hook

```typescript
// hooks/useConfig.ts
import { useState, useEffect, useCallback } from 'react';
import * as adminApi from '../services/adminApi';

export function useConfig(configId: string) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminApi.getConfig(configId);
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [configId]);

  const save = async (newData: any) => {
    const response = await adminApi.saveConfig(configId, newData);
    if (response.success) {
      setData(newData);
    }
    return response;
  };

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, reload: load, save };
}
```

## Config Definition Schema

```python
{
    'config_id': {
        'path': str,           # Required: Path to config file
        'name': str,           # Required: Display name
        'description': str,    # Optional: Description
        'category': str,       # Optional: Grouping (core, models, ui, business)
    }
}
```

## Hot-Reload Support

Register callbacks for when configs are reloaded:

```python
def reload_credits():
    from shared.credits import reload_config
    reload_config()

admin_router = create_admin_router(
    config_definitions=CONFIG_DEFINITIONS,
    require_admin=require_admin,
    reload_callbacks={
        'credits': reload_credits,
        'backend': lambda: app.state.config.reload(),
    }
)
```

## Security

**Always protect admin endpoints with authentication!**

```python
# Good - protected
router = create_admin_router(
    config_definitions=configs,
    require_admin=require_admin  # Your auth dependency
)

# Bad - unprotected (dev only!)
router = create_admin_router(
    config_definitions=configs,
    require_admin=None  # Anyone can modify configs!
)
```

## Error Handling

The module raises specific exceptions:

```python
from shared.admin.config_manager import (
    ConfigNotFoundError,    # File doesn't exist
    ConfigParseError,       # Invalid YAML/JSON
    ConfigSaveError,        # Failed to write
    SectionNotFoundError,   # Dot-path not found
)

from shared.admin.backup_manager import (
    BackupNotFoundError,    # Backup file missing
)
```

## Dependencies

Required:
- `pydantic>=2.0`
- `fastapi>=0.100.0`

Optional:
- `pyyaml>=6.0` (for YAML support)
