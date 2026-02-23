"""
Backup Manager
==============
Manages configuration file backups with listing and restore functionality.

Usage:
-----
```python
from shared.admin import BackupManager

manager = BackupManager(backup_dir='./config_backups')

# List all backups
backups = manager.list_backups()

# Restore a specific backup
manager.restore('backend_20240115_103045.yaml', 'config.yaml')

# Clean old backups (keep last 10)
deleted = manager.cleanup(keep_count=10)
```
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union
from datetime import datetime


class BackupError(Exception):
    """Base exception for backup operations."""
    pass


class BackupNotFoundError(BackupError):
    """Raised when a backup file is not found."""
    pass


class BackupManager:
    """
    Manages configuration file backups.
    
    Provides:
    - Backup listing with metadata
    - Restore from backup
    - Cleanup of old backups
    - Backup organization by config type
    """
    
    def __init__(self, backup_dir: Union[str, Path] = 'config_backups'):
        """
        Initialize BackupManager.
        
        Args:
            backup_dir: Directory for storing backups.
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def list_backups(
        self,
        config_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[dict]:
        """
        List all available backups.
        
        Args:
            config_name: Filter by config name (e.g., 'backend' matches 'backend_*.yaml').
            limit: Maximum number of backups to return.
            
        Returns:
            List of backup info dicts sorted by creation date (newest first).
        """
        backups = []
        
        if not self.backup_dir.exists():
            return []
        
        for file in self.backup_dir.iterdir():
            if not file.is_file():
                continue
            
            # Filter by config name if specified
            if config_name and not file.stem.startswith(config_name):
                continue
            
            stat = file.stat()
            backups.append({
                'filename': file.name,
                'path': str(file),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'config_name': self._extract_config_name(file.name)
            })
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        if limit:
            backups = backups[:limit]
        
        return backups
    
    def _extract_config_name(self, filename: str) -> str:
        """Extract the original config name from backup filename."""
        # Format: configname_YYYYMMDD_HHMMSS.ext
        parts = filename.rsplit('_', 2)
        if len(parts) >= 3:
            return parts[0]
        return filename.rsplit('.', 1)[0]
    
    def restore(
        self,
        backup_filename: str,
        target_path: Union[str, Path],
        create_current_backup: bool = True
    ) -> Optional[str]:
        """
        Restore a configuration from backup.
        
        Args:
            backup_filename: Name of the backup file to restore.
            target_path: Path to restore the configuration to.
            create_current_backup: Whether to backup current config before restoring.
            
        Returns:
            Path to the backup of current config (if created), None otherwise.
            
        Raises:
            BackupNotFoundError: If backup file doesn't exist.
        """
        backup_path = self.backup_dir / backup_filename
        target_path = Path(target_path)
        
        if not backup_path.exists():
            raise BackupNotFoundError(f"Backup not found: {backup_filename}")
        
        current_backup_path = None
        
        # Backup current config before restoring
        if create_current_backup and target_path.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            current_backup_name = f"{target_path.stem}_pre_restore_{timestamp}{target_path.suffix}"
            current_backup_path = self.backup_dir / current_backup_name
            shutil.copy2(target_path, current_backup_path)
        
        # Restore the backup
        shutil.copy2(backup_path, target_path)
        
        return str(current_backup_path) if current_backup_path else None
    
    def get_backup_info(self, backup_filename: str) -> dict:
        """
        Get detailed information about a specific backup.
        
        Args:
            backup_filename: Name of the backup file.
            
        Returns:
            Dictionary with backup metadata.
            
        Raises:
            BackupNotFoundError: If backup doesn't exist.
        """
        backup_path = self.backup_dir / backup_filename
        
        if not backup_path.exists():
            raise BackupNotFoundError(f"Backup not found: {backup_filename}")
        
        stat = backup_path.stat()
        
        # Try to read content preview
        preview = None
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read(500)
                preview = content[:500] + ('...' if len(content) >= 500 else '')
        except Exception:
            pass
        
        return {
            'filename': backup_filename,
            'path': str(backup_path),
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'config_name': self._extract_config_name(backup_filename),
            'preview': preview
        }
    
    def cleanup(
        self,
        keep_count: int = 10,
        config_name: Optional[str] = None,
        older_than_days: Optional[int] = None
    ) -> List[str]:
        """
        Remove old backups.
        
        Args:
            keep_count: Number of most recent backups to keep per config.
            config_name: Only cleanup backups for this config (None = all).
            older_than_days: Only delete backups older than this many days.
            
        Returns:
            List of deleted backup filenames.
        """
        deleted = []
        
        # Group backups by config name
        backups_by_config: dict[str, List[dict]] = {}
        for backup in self.list_backups():
            cfg_name = backup['config_name']
            if config_name and cfg_name != config_name:
                continue
            if cfg_name not in backups_by_config:
                backups_by_config[cfg_name] = []
            backups_by_config[cfg_name].append(backup)
        
        cutoff_date = None
        if older_than_days:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
        
        # Cleanup each config's backups
        for cfg_name, backups in backups_by_config.items():
            # Sort by date (newest first)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
            for i, backup in enumerate(backups):
                should_delete = False
                
                # Delete if beyond keep_count
                if i >= keep_count:
                    should_delete = True
                
                # Delete if older than cutoff
                if cutoff_date:
                    backup_date = datetime.fromisoformat(backup['created'])
                    if backup_date < cutoff_date:
                        should_delete = True
                
                if should_delete:
                    try:
                        os.remove(backup['path'])
                        deleted.append(backup['filename'])
                    except Exception:
                        pass
        
        return deleted
    
    def delete_backup(self, backup_filename: str) -> bool:
        """
        Delete a specific backup file.
        
        Args:
            backup_filename: Name of the backup to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        backup_path = self.backup_dir / backup_filename
        
        if not backup_path.exists():
            return False
        
        os.remove(backup_path)
        return True
