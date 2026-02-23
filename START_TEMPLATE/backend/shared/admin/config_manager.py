"""
Configuration Manager
=====================
Core class for managing YAML and JSON configuration files.

Provides:
- Load/save with automatic format detection
- Dot-notation access for nested values
- Thread-safe operations
- Validation hooks

Usage:
-----
```python
from shared.admin import ConfigManager

manager = ConfigManager()

# Load a config file
config = manager.load('config.yaml')

# Get nested value using dot notation
heading_font = manager.get_value(config, 'appearance.fonts.heading')

# Set nested value
config = manager.set_value(config, 'appearance.fonts.heading', 'Inter')

# Save with automatic backup
backup_path = manager.save('config.yaml', config, create_backup=True)
```
"""

import os
import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from datetime import datetime

# Try to import yaml, provide helpful error if missing
try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


class ConfigManagerError(Exception):
    """Base exception for ConfigManager errors."""
    pass


class ConfigNotFoundError(ConfigManagerError):
    """Raised when a configuration file is not found."""
    pass


class ConfigParseError(ConfigManagerError):
    """Raised when a configuration file cannot be parsed."""
    pass


class ConfigSaveError(ConfigManagerError):
    """Raised when a configuration file cannot be saved."""
    pass


class SectionNotFoundError(ConfigManagerError):
    """Raised when a section path doesn't exist in config."""
    pass


class ConfigManager:
    """
    Manages YAML and JSON configuration files with dot-notation access.
    
    Thread-safe operations with support for:
    - Automatic format detection (YAML/JSON)
    - Nested value access via dot notation
    - Backup creation on save
    - File validation
    
    Attributes:
        backup_dir: Directory for storing backups (default: 'config_backups')
        encoding: File encoding (default: 'utf-8')
    """
    
    def __init__(
        self,
        backup_dir: Optional[Union[str, Path]] = None,
        encoding: str = 'utf-8'
    ):
        """
        Initialize ConfigManager.
        
        Args:
            backup_dir: Directory for backups. If None, creates 'config_backups' 
                       next to the config file.
            encoding: File encoding for read/write operations.
        """
        self.backup_dir = Path(backup_dir) if backup_dir else None
        self.encoding = encoding
        self._lock = threading.Lock()
    
    # =========================================================================
    # File Operations
    # =========================================================================
    
    def load(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load a configuration file.
        
        Automatically detects format based on file extension:
        - .yaml, .yml → YAML
        - .json → JSON
        
        Args:
            path: Path to the configuration file.
            
        Returns:
            Parsed configuration as dictionary.
            
        Raises:
            ConfigNotFoundError: If file doesn't exist.
            ConfigParseError: If file cannot be parsed.
        """
        path = Path(path)
        
        if not path.exists():
            raise ConfigNotFoundError(f"Configuration file not found: {path}")
        
        try:
            with self._lock:
                with open(path, 'r', encoding=self.encoding) as f:
                    content = f.read()
                    
                    if path.suffix.lower() in ('.yaml', '.yml'):
                        if yaml is None:
                            raise ConfigParseError(
                                "PyYAML is required for YAML files. "
                                "Install with: pip install pyyaml"
                            )
                        return yaml.safe_load(content) or {}
                    
                    elif path.suffix.lower() == '.json':
                        return json.loads(content) if content.strip() else {}
                    
                    else:
                        # Try YAML first, then JSON
                        if yaml:
                            try:
                                return yaml.safe_load(content) or {}
                            except Exception:
                                pass
                        try:
                            return json.loads(content) if content.strip() else {}
                        except Exception:
                            raise ConfigParseError(
                                f"Cannot determine format for: {path}. "
                                "Use .yaml, .yml, or .json extension."
                            )
        except (ConfigNotFoundError, ConfigParseError):
            raise
        except Exception as e:
            raise ConfigParseError(f"Failed to parse {path}: {e}")
    
    def save(
        self,
        path: Union[str, Path],
        data: Dict[str, Any],
        create_backup: bool = True,
        backup_dir: Optional[Union[str, Path]] = None
    ) -> Optional[str]:
        """
        Save configuration to file.
        
        Args:
            path: Path to save the configuration.
            data: Configuration data to save.
            create_backup: Whether to backup existing file before saving.
            backup_dir: Override backup directory for this save.
            
        Returns:
            Path to backup file if created, None otherwise.
            
        Raises:
            ConfigSaveError: If file cannot be saved.
        """
        path = Path(path)
        backup_path = None
        
        try:
            with self._lock:
                # Create backup if file exists
                if create_backup and path.exists():
                    backup_path = self._create_backup(path, backup_dir)
                
                # Ensure parent directory exists
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file
                with open(path, 'w', encoding=self.encoding) as f:
                    if path.suffix.lower() in ('.yaml', '.yml'):
                        if yaml is None:
                            raise ConfigSaveError(
                                "PyYAML is required for YAML files. "
                                "Install with: pip install pyyaml"
                            )
                        yaml.dump(
                            data, f,
                            default_flow_style=False,
                            sort_keys=False,
                            allow_unicode=True
                        )
                    else:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                
                return str(backup_path) if backup_path else None
                
        except Exception as e:
            raise ConfigSaveError(f"Failed to save {path}: {e}")
    
    def _create_backup(
        self,
        path: Path,
        backup_dir: Optional[Union[str, Path]] = None
    ) -> Path:
        """Create a backup of a configuration file."""
        import shutil
        
        # Determine backup directory
        bkp_dir = Path(backup_dir) if backup_dir else self.backup_dir
        if bkp_dir is None:
            bkp_dir = path.parent / 'config_backups'
        
        bkp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{path.stem}_{timestamp}{path.suffix}"
        backup_path = bkp_dir / backup_name
        
        shutil.copy2(path, backup_path)
        return backup_path
    
    # =========================================================================
    # Dot-Notation Access
    # =========================================================================
    
    def get_value(
        self,
        config: Dict[str, Any],
        path: str,
        default: Any = None
    ) -> Any:
        """
        Get a nested value using dot notation.
        
        Examples:
            get_value(config, 'appearance.fonts.heading')
            get_value(config, 'models.flux', default={})
        
        Args:
            config: Configuration dictionary.
            path: Dot-separated path to the value.
            default: Value to return if path not found.
            
        Returns:
            Value at path, or default if not found.
        """
        keys = path.split('.')
        result = config
        
        try:
            for key in keys:
                if isinstance(result, dict) and key in result:
                    result = result[key]
                else:
                    return default
            return result
        except Exception:
            return default
    
    def get_value_strict(
        self,
        config: Dict[str, Any],
        path: str
    ) -> Any:
        """
        Get a nested value using dot notation (raises on not found).
        
        Args:
            config: Configuration dictionary.
            path: Dot-separated path to the value.
            
        Returns:
            Value at path.
            
        Raises:
            SectionNotFoundError: If path doesn't exist.
        """
        keys = path.split('.')
        result = config
        current_path = []
        
        for key in keys:
            current_path.append(key)
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                raise SectionNotFoundError(
                    f"Section '{'.'.join(current_path)}' not found in config"
                )
        
        return result
    
    def set_value(
        self,
        config: Dict[str, Any],
        path: str,
        value: Any
    ) -> Dict[str, Any]:
        """
        Set a nested value using dot notation.
        
        Creates intermediate dictionaries if they don't exist.
        
        Examples:
            set_value(config, 'appearance.fonts.heading', 'Inter')
            set_value(config, 'new.nested.value', {'key': 'value'})
        
        Args:
            config: Configuration dictionary (modified in place).
            path: Dot-separated path to set.
            value: Value to set.
            
        Returns:
            Modified configuration dictionary.
        """
        keys = path.split('.')
        current = config
        
        # Navigate/create path
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        # Set the value
        current[keys[-1]] = value
        return config
    
    def delete_value(
        self,
        config: Dict[str, Any],
        path: str
    ) -> Dict[str, Any]:
        """
        Delete a nested value using dot notation.
        
        Args:
            config: Configuration dictionary (modified in place).
            path: Dot-separated path to delete.
            
        Returns:
            Modified configuration dictionary.
            
        Raises:
            SectionNotFoundError: If path doesn't exist.
        """
        keys = path.split('.')
        current = config
        
        # Navigate to parent
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise SectionNotFoundError(f"Path '{path}' not found")
        
        # Delete the key
        if keys[-1] in current:
            del current[keys[-1]]
        else:
            raise SectionNotFoundError(f"Path '{path}' not found")
        
        return config
    
    # =========================================================================
    # Search
    # =========================================================================
    
    def search(
        self,
        config: Dict[str, Any],
        query: str,
        case_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for a query string in keys and values.
        
        Args:
            config: Configuration dictionary to search.
            query: Search string.
            case_sensitive: Whether search is case-sensitive.
            
        Returns:
            List of matches with path, type ('key' or 'value'), and match string.
        """
        matches = []
        search_query = query if case_sensitive else query.lower()
        
        def search_recursive(obj: Any, path: str = ''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    key_str = key if case_sensitive else key.lower()
                    
                    # Check key
                    if search_query in key_str:
                        matches.append({
                            'path': current_path,
                            'type': 'key',
                            'match': key
                        })
                    
                    # Recurse
                    search_recursive(value, current_path)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    search_recursive(item, f"{path}[{i}]")
                    
            elif isinstance(obj, (str, int, float, bool)):
                value_str = str(obj) if case_sensitive else str(obj).lower()
                if search_query in value_str:
                    matches.append({
                        'path': path,
                        'type': 'value',
                        'match': str(obj)
                    })
        
        search_recursive(config)
        return matches
    
    # =========================================================================
    # Metadata
    # =========================================================================
    
    def get_metadata(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get file metadata.
        
        Args:
            path: Path to the configuration file.
            
        Returns:
            Dictionary with exists, size, last_modified, format.
        """
        path = Path(path)
        
        if not path.exists():
            return {
                'exists': False,
                'size': 0,
                'last_modified': None,
                'format': None
            }
        
        stat = path.stat()
        return {
            'exists': True,
            'size': stat.st_size,
            'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'format': 'yaml' if path.suffix.lower() in ('.yaml', '.yml') else 'json'
        }
    
    # =========================================================================
    # Validation
    # =========================================================================
    
    def validate_yaml(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Validate YAML content without saving.
        
        Args:
            content: YAML string to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        if yaml is None:
            return False, "PyYAML not installed"
        
        try:
            yaml.safe_load(content)
            return True, None
        except yaml.YAMLError as e:
            return False, str(e)
    
    def validate_json(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Validate JSON content without saving.
        
        Args:
            content: JSON string to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            json.loads(content)
            return True, None
        except json.JSONDecodeError as e:
            return False, str(e)
