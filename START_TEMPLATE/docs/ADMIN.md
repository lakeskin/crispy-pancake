# Admin Panel System

A complete, reusable admin panel for managing YAML/JSON configurations with automatic backups, search, and hot-reload support.

## 🎯 Overview

This module provides everything you need to build an admin panel for your application:

| Layer | Components | Purpose |
|-------|------------|---------|
| **Backend** | `ConfigManager`, `BackupManager`, `create_admin_router()` | YAML/JSON CRUD, backups, REST API |
| **Frontend** | `ConfigEditor`, `BackupManager`, `useConfig()` | React components and hooks |

## 📦 What's Included

### Backend (`backend/shared/admin/`)

```
admin/
├── __init__.py           # Module exports
├── config_manager.py     # Core YAML/JSON operations
├── backup_manager.py     # Backup/restore functionality
├── router_factory.py     # FastAPI router generator
├── models.py             # Pydantic response models
├── config.yaml           # Default settings
└── README.md             # Backend documentation
```

### Frontend (`frontend/src/`)

```
services/
└── adminApi.ts           # API client factory

hooks/
└── useConfig.ts          # React hooks for config state

components/admin/
├── ConfigEditor.tsx      # Form-based config editor
├── BackupManager.tsx     # Backup list and restore UI
└── index.ts              # Exports
```

---

## 🚀 Quick Start

### 1. Backend Setup

```python
# main.py
from fastapi import FastAPI
from shared.admin import create_admin_router
from shared.auth.decorators import require_admin  # Your auth

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
        'description': 'UI appearance',
        'category': 'ui'
    },
    'credits': {
        'path': 'shared/credits/config.yaml',
        'name': 'Pricing',
        'description': 'Credit packages and costs',
        'category': 'business'
    }
}

# Create router with admin protection
admin_router = create_admin_router(
    config_definitions=CONFIG_DEFINITIONS,
    require_admin=require_admin,
    prefix="/api/admin",
    backup_dir="./config_backups"
)

app = FastAPI()
app.include_router(admin_router)
```

### 2. Frontend Setup

```tsx
// pages/AdminPanel.tsx
import { ConfigEditor, BackupManager } from '../components/admin';

export default function AdminPanel() {
  return (
    <div>
      <h1>Admin Panel</h1>
      
      {/* Edit backend config */}
      <ConfigEditor
        configId="backend"
        title="Backend Settings"
        description="Main application configuration"
      />
      
      {/* Edit specific section */}
      <ConfigEditor
        configId="theme"
        sectionPath="appearance.fonts"
        title="Font Settings"
      />
      
      {/* Backup management */}
      <BackupManager />
    </div>
  );
}
```

---

## 🔌 API Endpoints

When you use `create_admin_router()`, these endpoints are automatically created:

### Config Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/admin/configs` | List all configuration files |
| `GET` | `/api/admin/configs/{id}` | Get full config contents |
| `PUT` | `/api/admin/configs/{id}` | Save full config (with backup) |
| `GET` | `/api/admin/configs/{id}/{path}` | Get section via dot notation |
| `PUT` | `/api/admin/configs/{id}/{path}` | Save section |
| `GET` | `/api/admin/configs/search?q=...` | Search across all configs |
| `POST` | `/api/admin/configs/reload` | Trigger hot-reload |

### Backup Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/admin/backups` | List all backups |
| `POST` | `/api/admin/backups/{file}/restore` | Restore a backup |
| `DELETE` | `/api/admin/backups/{file}` | Delete a backup |
| `POST` | `/api/admin/backups/cleanup` | Remove old backups |

---

## 📝 Usage Examples

### Using ConfigManager Directly

```python
from shared.admin import ConfigManager

manager = ConfigManager()

# Load config
config = manager.load('config.yaml')

# Dot-notation access
font = manager.get_value(config, 'appearance.fonts.heading')
timeout = manager.get_value(config, 'api.timeout', default=30)

# Update nested value
config = manager.set_value(config, 'appearance.fonts.heading', 'Inter')

# Save with automatic backup
backup = manager.save('config.yaml', config, create_backup=True)
print(f"Backup created: {backup}")

# Search
matches = manager.search(config, 'font')
```

### Using BackupManager

```python
from shared.admin import BackupManager

backups = BackupManager('./config_backups')

# List backups
for b in backups.list_backups():
    print(f"{b['filename']} - {b['created']}")

# Restore
backups.restore('theme_20240115_103045.json', 'theme.json')

# Cleanup (keep last 10 per config)
deleted = backups.cleanup(keep_count=10)
```

### Using React Hooks

```tsx
import { useConfig, useConfigSection } from '../hooks/useConfig';

// Full config
function BackendEditor() {
  const { data, loading, save, isDirty } = useConfig('backend');
  
  if (loading) return <Loading />;
  
  return (
    <Form
      data={data}
      onSave={async (newData) => {
        const result = await save(newData);
        if (result.success) toast.success('Saved!');
      }}
    />
  );
}

// Specific section
function FontEditor() {
  const { data, save } = useConfigSection('theme', 'appearance.fonts');
  
  return (
    <FontPicker
      value={data?.heading}
      onChange={(font) => save({ ...data, heading: font })}
    />
  );
}
```

---

## ⚙️ Configuration

### Config Definition Schema

```python
{
    'config_id': {
        'path': str,           # Required: Path to config file
        'name': str,           # Required: Display name
        'description': str,    # Optional: Description text
        'category': str,       # Optional: Grouping category
    }
}
```

**Categories:** `core`, `models`, `ui`, `business`, `system`

### Router Factory Options

```python
create_admin_router(
    config_definitions=CONFIG_DEFINITIONS,  # Required: Config file definitions
    require_admin=require_admin,            # Required: Auth dependency (or None for dev)
    prefix="/api/admin",                    # API prefix
    backup_dir="./config_backups",          # Backup storage location
    base_path=Path.cwd(),                   # Base for relative paths
    reload_callbacks={                      # Hot-reload callbacks
        'credits': lambda: reload_credits(),
    },
    logger=my_logger,                       # Custom logger
    tags=["Admin"],                         # OpenAPI tags
)
```

---

## 🔐 Security

**⚠️ CRITICAL: Always protect admin endpoints with authentication!**

```python
# ✅ GOOD - Protected
router = create_admin_router(
    config_definitions=configs,
    require_admin=require_admin  # Your auth dependency
)

# ❌ BAD - Unprotected (anyone can modify configs!)
router = create_admin_router(
    config_definitions=configs,
    require_admin=None  # NEVER in production!
)
```

---

## 🔄 Hot-Reload Support

Register callbacks for when configs are reloaded:

```python
def reload_credits():
    from shared.credits import reload_config
    reload_config()

router = create_admin_router(
    config_definitions=configs,
    require_admin=require_admin,
    reload_callbacks={
        'credits': reload_credits,
        'backend': lambda: app.state.config.reload(),
    }
)
```

When `POST /api/admin/configs/reload` is called, all registered callbacks execute.

---

## 🎨 Frontend Components

### ConfigEditor

Generic form-based config editor:

```tsx
<ConfigEditor
  configId="backend"
  sectionPath="appearance.fonts"  // Optional: specific section
  title="Font Settings"
  description="Configure typography"
  fieldConfig={{                  // Optional: customize fields
    heading: { type: 'select', options: fonts },
    body_weight: { type: 'number', min: 100, max: 900 },
  }}
  excludeFields={['internal_id']} // Optional: hide fields
  onSave={(result) => toast.success('Saved!')}
  onError={(msg) => toast.error(msg)}
/>
```

### BackupManager

Backup listing and restore UI:

```tsx
<BackupManager
  configId="backend"              // Optional: filter by config
  limit={20}                      // Max backups shown
  onRestore={() => refetch()}     // Called after restore
  title="Configuration Backups"
/>
```

---

## 🐛 Error Handling

Backend exceptions:

```python
from shared.admin.config_manager import (
    ConfigNotFoundError,    # File doesn't exist
    ConfigParseError,       # Invalid YAML/JSON
    ConfigSaveError,        # Write failed
    SectionNotFoundError,   # Dot-path not found
)

from shared.admin.backup_manager import (
    BackupNotFoundError,    # Backup file missing
)
```

Frontend error handling:

```tsx
const { error } = useConfig('backend');

if (error) {
  return <Alert severity="error">{error}</Alert>;
}
```

---

## 📋 Dependencies

**Backend:**
- `pydantic>=2.0` (models)
- `fastapi>=0.100.0` (router)
- `pyyaml>=6.0` (YAML support - optional but recommended)

**Frontend:**
- React 18+
- Material-UI v5+ (for provided components)

---

## 🔗 Related Documentation

- [Backend README](../backend/shared/admin/README.md) - Detailed backend API
- [Auth Module](./AUTH.md) - Authentication for admin protection
- [Logging Module](./LOGGING.md) - Logging admin operations
