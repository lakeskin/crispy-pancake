"""
Admin Router Factory
====================
Creates FastAPI router with CRUD endpoints for configuration management.

Usage:
-----
```python
from fastapi import FastAPI, Depends
from shared.admin import create_admin_router

# Define your configuration files
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

# Create router with admin authentication
router = create_admin_router(
    config_definitions=config_definitions,
    require_admin=require_admin,  # Your admin auth dependency
    prefix="/api/admin",
    backup_dir="./config_backups"
)

# Include in your app
app = FastAPI()
app.include_router(router)
```

Generated Endpoints:
------------------
- GET    /api/admin/configs                    - List all configs
- GET    /api/admin/configs/{config_id}        - Get full config
- PUT    /api/admin/configs/{config_id}        - Save full config
- GET    /api/admin/configs/{config_id}/{path} - Get section (dot notation)
- PUT    /api/admin/configs/{config_id}/{path} - Save section
- POST   /api/admin/configs/reload             - Hot-reload all configs
- GET    /api/admin/configs/search             - Search across configs
- GET    /api/admin/backups                    - List backups
- POST   /api/admin/backups/{filename}/restore - Restore backup
- DELETE /api/admin/backups/{filename}         - Delete backup
- POST   /api/admin/backups/cleanup            - Cleanup old backups
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Any, Callable, Dict, Optional, Union
from pathlib import Path
import logging

from .config_manager import ConfigManager, ConfigNotFoundError, SectionNotFoundError
from .backup_manager import BackupManager, BackupNotFoundError
from .models import (
    ConfigListItem,
    ConfigResponse,
    SaveConfigResponse,
    SectionResponse,
    SearchResponse,
    SearchResult,
    SearchMatch,
    BackupListResponse,
    BackupItem,
    RestoreResponse,
    ReloadResponse,
    SaveConfigRequest,
    SaveSectionRequest,
    CleanupRequest,
)


def create_admin_router(
    config_definitions: Dict[str, Dict[str, Any]],
    require_admin: Optional[Callable] = None,
    prefix: str = "/api/admin",
    backup_dir: Union[str, Path] = "config_backups",
    base_path: Optional[Path] = None,
    reload_callbacks: Optional[Dict[str, Callable]] = None,
    logger: Optional[logging.Logger] = None,
    tags: Optional[list] = None,
) -> APIRouter:
    """
    Create a FastAPI router with admin configuration endpoints.
    
    Args:
        config_definitions: Dictionary mapping config IDs to their definitions.
            Each definition should have: path, name, description, category.
        require_admin: FastAPI dependency for admin authentication.
            If None, endpoints are unprotected (use for dev only!).
        prefix: URL prefix for all endpoints.
        backup_dir: Directory for storing config backups.
        base_path: Base path for resolving relative config paths.
        reload_callbacks: Dict of config_id -> callable to invoke on reload.
        logger: Logger instance for logging operations.
        tags: OpenAPI tags for the router.
        
    Returns:
        Configured FastAPI APIRouter.
    """
    router = APIRouter(prefix=prefix, tags=tags or ["Admin"])
    
    # Initialize managers
    config_manager = ConfigManager(backup_dir=backup_dir)
    backup_manager = BackupManager(backup_dir=backup_dir)
    
    # Set base path for resolving relative paths
    _base_path = Path(base_path) if base_path else Path.cwd()
    
    # Logger
    _logger = logger or logging.getLogger(__name__)
    
    # Reload callbacks
    _reload_callbacks = reload_callbacks or {}
    
    def _resolve_path(config_id: str) -> Path:
        """Resolve config path to absolute path."""
        if config_id not in config_definitions:
            raise HTTPException(status_code=404, detail=f"Unknown config: {config_id}")
        
        path = Path(config_definitions[config_id]['path'])
        if not path.is_absolute():
            path = _base_path / path
        return path
    
    def _get_config_info(config_id: str) -> dict:
        """Get config definition."""
        if config_id not in config_definitions:
            raise HTTPException(status_code=404, detail=f"Unknown config: {config_id}")
        return config_definitions[config_id]
    
    # Build dependencies list
    dependencies = [Depends(require_admin)] if require_admin else []
    
    # =========================================================================
    # List Configs
    # =========================================================================
    
    @router.get("/configs", response_model=Dict[str, Any], dependencies=dependencies)
    async def list_configs():
        """List all available configuration files with metadata."""
        result = []
        
        for config_id, config_info in config_definitions.items():
            path = _resolve_path(config_id)
            metadata = config_manager.get_metadata(path)
            
            result.append(ConfigListItem(
                id=config_id,
                name=config_info.get('name', config_id),
                description=config_info.get('description', ''),
                category=config_info.get('category', 'core'),
                path=str(path),
                exists=metadata['exists'],
                size=metadata['size'],
                last_modified=metadata['last_modified'],
                format=metadata['format']
            ).model_dump())
        
        return {'success': True, 'configs': result}
    
    # =========================================================================
    # Get Full Config
    # =========================================================================
    
    @router.get("/configs/{config_id}", response_model=ConfigResponse, dependencies=dependencies)
    async def get_config(config_id: str):
        """Get the full contents of a configuration file."""
        config_info = _get_config_info(config_id)
        path = _resolve_path(config_id)
        
        try:
            data = config_manager.load(path)
            metadata = config_manager.get_metadata(path)
            
            return ConfigResponse(
                success=True,
                config_id=config_id,
                name=config_info.get('name', config_id),
                data=data,
                path=str(path),
                last_modified=metadata['last_modified']
            )
        except ConfigNotFoundError:
            raise HTTPException(status_code=404, detail=f"Config file not found: {path}")
        except Exception as e:
            _logger.error(f"Failed to load config {config_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =========================================================================
    # Save Full Config
    # =========================================================================
    
    @router.put("/configs/{config_id}", response_model=SaveConfigResponse, dependencies=dependencies)
    async def save_config(config_id: str, request: SaveConfigRequest):
        """Save full contents of a configuration file."""
        path = _resolve_path(config_id)
        
        try:
            backup_path = config_manager.save(path, request.data, create_backup=True)
            _logger.info(f"Saved config {config_id} to {path}")
            
            return SaveConfigResponse(
                success=True,
                message=f"Config '{config_id}' saved successfully",
                backup_path=backup_path
            )
        except Exception as e:
            _logger.error(f"Failed to save config {config_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =========================================================================
    # Get Config Section
    # =========================================================================
    
    @router.get("/configs/{config_id}/{section_path:path}", response_model=SectionResponse, dependencies=dependencies)
    async def get_config_section(config_id: str, section_path: str):
        """Get a specific section using dot notation (e.g., 'appearance.fonts')."""
        path = _resolve_path(config_id)
        
        try:
            data = config_manager.load(path)
            section = config_manager.get_value_strict(data, section_path)
            
            return SectionResponse(
                success=True,
                config_id=config_id,
                section=section_path,
                data=section
            )
        except SectionNotFoundError:
            raise HTTPException(status_code=404, detail=f"Section '{section_path}' not found")
        except ConfigNotFoundError:
            raise HTTPException(status_code=404, detail=f"Config file not found")
        except Exception as e:
            _logger.error(f"Failed to get section {section_path} from {config_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =========================================================================
    # Save Config Section
    # =========================================================================
    
    @router.put("/configs/{config_id}/{section_path:path}", response_model=SaveConfigResponse, dependencies=dependencies)
    async def save_config_section(config_id: str, section_path: str, request: SaveSectionRequest):
        """Save a specific section using dot notation."""
        path = _resolve_path(config_id)
        
        try:
            # Load existing config
            data = config_manager.load(path)
            
            # Update section
            config_manager.set_value(data, section_path, request.data)
            
            # Save with backup
            backup_path = config_manager.save(path, data, create_backup=True)
            _logger.info(f"Saved section {section_path} in config {config_id}")
            
            return SaveConfigResponse(
                success=True,
                message=f"Section '{section_path}' saved successfully",
                backup_path=backup_path
            )
        except Exception as e:
            _logger.error(f"Failed to save section {section_path}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =========================================================================
    # Search Configs
    # =========================================================================
    
    @router.get("/configs/search", response_model=SearchResponse, dependencies=dependencies)
    async def search_configs(
        q: str = Query(..., min_length=1, description="Search query"),
        case_sensitive: bool = Query(False, description="Case-sensitive search")
    ):
        """Search across all configurations for a query string."""
        results = []
        total_matches = 0
        
        for config_id, config_info in config_definitions.items():
            path = _resolve_path(config_id)
            
            try:
                data = config_manager.load(path)
                matches = config_manager.search(data, q, case_sensitive)
                
                if matches:
                    total_matches += len(matches)
                    results.append(SearchResult(
                        config_id=config_id,
                        config_name=config_info.get('name', config_id),
                        matches=[SearchMatch(**m) for m in matches]
                    ))
            except Exception as e:
                _logger.warning(f"Failed to search {config_id}: {e}")
        
        return SearchResponse(
            success=True,
            query=q,
            results=results,
            total_matches=total_matches
        )
    
    # =========================================================================
    # Reload Configs
    # =========================================================================
    
    @router.post("/configs/reload", response_model=ReloadResponse, dependencies=dependencies)
    async def reload_configs():
        """Trigger hot-reload of configuration files."""
        reloaded = []
        errors = []
        
        for config_id in config_definitions:
            try:
                if config_id in _reload_callbacks:
                    _reload_callbacks[config_id]()
                reloaded.append(config_id)
            except Exception as e:
                errors.append({'config': config_id, 'error': str(e)})
        
        return ReloadResponse(
            success=len(errors) == 0,
            reloaded=reloaded,
            errors=errors,
            message='Configs reloaded successfully' if not errors else 'Some configs failed to reload'
        )
    
    # =========================================================================
    # List Backups
    # =========================================================================
    
    @router.get("/backups", response_model=BackupListResponse, dependencies=dependencies)
    async def list_backups(
        config_name: Optional[str] = Query(None, description="Filter by config name"),
        limit: Optional[int] = Query(50, description="Max backups to return")
    ):
        """List all configuration backups."""
        backups = backup_manager.list_backups(config_name=config_name, limit=limit)
        
        return BackupListResponse(
            success=True,
            backups=[BackupItem(**b) for b in backups],
            total=len(backups)
        )
    
    # =========================================================================
    # Restore Backup
    # =========================================================================
    
    @router.post("/backups/{filename}/restore", response_model=RestoreResponse, dependencies=dependencies)
    async def restore_backup(filename: str, config_id: str = Query(..., description="Target config ID")):
        """Restore a configuration from backup."""
        path = _resolve_path(config_id)
        
        try:
            previous = backup_manager.restore(filename, path, create_current_backup=True)
            _logger.info(f"Restored {filename} to {config_id}")
            
            return RestoreResponse(
                success=True,
                message=f"Successfully restored {filename}",
                restored_from=filename,
                restored_to=str(path),
                previous_backup=previous
            )
        except BackupNotFoundError:
            raise HTTPException(status_code=404, detail=f"Backup not found: {filename}")
        except Exception as e:
            _logger.error(f"Failed to restore backup {filename}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =========================================================================
    # Delete Backup
    # =========================================================================
    
    @router.delete("/backups/{filename}", dependencies=dependencies)
    async def delete_backup(filename: str):
        """Delete a specific backup file."""
        if backup_manager.delete_backup(filename):
            return {'success': True, 'message': f"Deleted backup: {filename}"}
        else:
            raise HTTPException(status_code=404, detail=f"Backup not found: {filename}")
    
    # =========================================================================
    # Cleanup Backups
    # =========================================================================
    
    @router.post("/backups/cleanup", dependencies=dependencies)
    async def cleanup_backups(request: CleanupRequest):
        """Remove old backups."""
        deleted = backup_manager.cleanup(
            keep_count=request.keep_count,
            config_name=request.config_name,
            older_than_days=request.older_than_days
        )
        
        return {
            'success': True,
            'deleted_count': len(deleted),
            'deleted': deleted
        }
    
    return router
