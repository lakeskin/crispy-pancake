"""
Shared Admin Module
===================
Reusable admin panel components for YAML/JSON configuration management.

This module provides:
- ConfigManager: Core YAML/JSON file operations with dot-notation access
- BackupManager: Automatic backup and restore functionality
- create_admin_router(): FastAPI router factory for config endpoints
- Pydantic models for type-safe API responses

Quick Start:
-----------
```python
from shared.admin import ConfigManager, create_admin_router

# Define your config files
config_definitions = {
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
    }
}

# Create router with CRUD endpoints
router = create_admin_router(config_definitions, require_admin_dependency)
app.include_router(router)
```

Features:
--------
- YAML and JSON file support
- Dot-notation access (e.g., "appearance.fonts.heading")
- Automatic backups before saves
- Backup listing and restore
- Search across all configs
- Hot-reload support
- FastAPI integration with dependency injection
"""

from .config_manager import ConfigManager
from .backup_manager import BackupManager
from .router_factory import create_admin_router
from .models import (
    ConfigDefinition,
    ConfigListItem,
    ConfigResponse,
    SaveConfigResponse,
    BackupItem,
    SearchResult,
    SearchMatch,
)

__all__ = [
    # Core classes
    'ConfigManager',
    'BackupManager',
    'create_admin_router',
    # Models
    'ConfigDefinition',
    'ConfigListItem',
    'ConfigResponse',
    'SaveConfigResponse',
    'BackupItem',
    'SearchResult',
    'SearchMatch',
]

__version__ = '1.0.0'
