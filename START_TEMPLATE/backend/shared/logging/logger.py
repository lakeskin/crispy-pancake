"""
Centralized logging system for all AsaadAsh applications

Features:
- App-level configuration (each app can have its own logging config)
- Multiple output destinations (console, file, New Relic)
- Structured JSON logging
- Automatic context injection
- Environment variable overrides
- Sensitive data filtering

Usage:
    from shared.logging import get_logger
    
    # Get logger with app context
    logger = get_logger(__name__, app_name='image_generator')
    
    # Simple logging
    logger.info("Server starting", port=5000)
    logger.debug("Config loaded", models_count=8)
    
    # Error logging with full context
    try:
        result = do_something()
    except Exception as e:
        logger.error("Operation failed",
                    error=e,
                    stack_trace=traceback.format_exc(),
                    user_id=user_id)
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import json
from datetime import datetime
import re


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, sensitive_patterns: List[str] = None):
        super().__init__()
        self.sensitive_patterns = sensitive_patterns or []
    
    def format(self, record):
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'filename': record.filename,
            'lineno': record.lineno,
            'funcName': record.funcName,
            'pathname': record.pathname,
        }
        
        # Add custom fields from extra parameter
        if hasattr(record, 'extra_data'):
            log_data.update(self._filter_sensitive(record.extra_data))
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)
    
    def _filter_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from log output"""
        filtered = {}
        for key, value in data.items():
            # Check if key matches sensitive patterns
            if any(re.search(pattern, key, re.IGNORECASE) for pattern in self.sensitive_patterns):
                filtered[key] = '***REDACTED***'
            elif isinstance(value, str):
                # Check if value contains sensitive data
                filtered[key] = value
            else:
                filtered[key] = value
        return filtered


class AppLogger:
    """
    Centralized logger with app-level configuration
    
    Configuration hierarchy:
    1. Environment variables (highest priority)
    2. App-level config (apps/<app_name>/logging.yaml)
    3. Global config (shared/logging/config.yaml)
    4. Defaults (lowest priority)
    """
    
    _instances = {}
    _global_config = None
    _newrelic_initialized = False  # Track if New Relic agent has been initialized
    
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    @classmethod
    def _load_global_config(cls):
        """Load global logging configuration"""
        if cls._global_config is None:
            config_path = Path(__file__).parent / 'config.yaml'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    cls._global_config = yaml.safe_load(f)
            else:
                # Default config
                cls._global_config = {
                    'level': 'INFO',
                    'format': 'json',
                    'outputs': ['console'],
                    'include_context': True,
                    'sensitive_patterns': ['password', 'api_key', 'token', 'secret', 'key'],
                    'newrelic': {
                        'enabled': False
                    }
                }
        return cls._global_config
    
    @classmethod
    def _load_app_config(cls, app_name: Optional[str] = None):
        """Load app-specific logging configuration"""
        if not app_name:
            return {}
        
        # Try to find app config in applications/<app_name>/logging.yaml
        repo_root = Path(__file__).parent.parent.parent
        app_config_path = repo_root / 'applications' / app_name / 'logging.yaml'
        
        if app_config_path.exists():
            with open(app_config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        
        return {}
    
    @classmethod
    def _merge_configs(cls, global_config: Dict, app_config: Dict, env_overrides: Dict) -> Dict:
        """Merge configuration from multiple sources"""
        # Start with global config
        merged = global_config.copy()
        
        # Override with app config
        for key, value in app_config.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key].update(value)
            else:
                merged[key] = value
        
        # Override with environment variables
        merged.update(env_overrides)
        
        return merged
    
    @classmethod
    def get_logger(cls, name: str, app_name: Optional[str] = None, **context):
        """
        Get or create a logger instance
        
        Args:
            name: Logger name (usually __name__)
            app_name: Application name for app-level config
            **context: Additional context to include in all logs
        
        Returns:
            AsaadLogger instance
        """
        cache_key = f"{app_name or 'global'}:{name}"
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls(name, app_name, **context)
        return cls._instances[cache_key]
    
    def __init__(self, name: str, app_name: Optional[str] = None, **context):
        self.name = name
        self.app_name = app_name
        self.context = context
        
        # Load and merge configurations
        global_config = self._load_global_config()
        app_config = self._load_app_config(app_name)
        env_overrides = self._get_env_overrides()
        
        self.config = self._merge_configs(global_config, app_config, env_overrides)
        
        # Apply environment-specific settings (development, staging, production)
        self._apply_environment_settings()
        
        # Create Python logger
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _apply_environment_settings(self):
        """Apply environment-specific settings from the 'environments' section"""
        environments = self.config.get('environments', {})
        if not environments:
            return
        
        # Determine current environment from FLASK_ENV or default to development
        current_env = os.environ.get('FLASK_ENV', 'development').lower()
        
        if current_env in environments:
            env_settings = environments[current_env]
            # Apply environment settings (they override the base config)
            for key, value in env_settings.items():
                self.config[key] = value
    
    def _get_env_overrides(self) -> Dict:
        """Get configuration overrides from environment variables"""
        overrides = {}
        
        # LOG_LEVEL override
        if 'LOG_LEVEL' in os.environ:
            overrides['level'] = os.environ['LOG_LEVEL']
        
        # LOG_FORMAT override
        if 'LOG_FORMAT' in os.environ:
            overrides['format'] = os.environ['LOG_FORMAT']
        
        # LOG_OUTPUTS override (comma-separated)
        if 'LOG_OUTPUTS' in os.environ:
            overrides['outputs'] = [o.strip() for o in os.environ['LOG_OUTPUTS'].split(',')]
        
        # New Relic overrides
        if 'NEW_RELIC_LICENSE_KEY' in os.environ:
            if 'newrelic' not in overrides:
                overrides['newrelic'] = {}
            overrides['newrelic']['enabled'] = True
            overrides['newrelic']['license_key'] = os.environ['NEW_RELIC_LICENSE_KEY']
        
        if 'NEW_RELIC_APP_NAME' in os.environ:
            if 'newrelic' not in overrides:
                overrides['newrelic'] = {}
            overrides['newrelic']['app_name'] = os.environ['NEW_RELIC_APP_NAME']
        
        return overrides
    
    def _setup_logger(self):
        """Configure logger with handlers and formatters"""
        # Get log level
        level_str = self.config.get('level', 'INFO')
        self.logger.setLevel(self.LOG_LEVELS.get(level_str.upper(), logging.INFO))
        
        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Get formatter
        formatter = self._get_formatter()
        
        # Console handler
        if 'console' in self.config.get('outputs', ['console']):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler
        if 'file' in self.config.get('outputs', []):
            log_dir = self._get_log_directory()
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f'{self.app_name or "app"}.log'
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # New Relic handler (if enabled)
        if self.config.get('newrelic', {}).get('enabled', False):
            self._setup_newrelic()
    
    def _get_log_directory(self) -> Path:
        """Get log directory path"""
        log_dir = self.config.get('log_directory')
        
        if log_dir:
            return Path(log_dir)
        
        # Default: logs/ in application directory or repo root
        if self.app_name:
            repo_root = Path(__file__).parent.parent.parent
            return repo_root / 'applications' / self.app_name / 'logs'
        else:
            return Path('logs')
    
    def _get_formatter(self):
        """Get log formatter based on config"""
        format_type = self.config.get('format', 'json')
        sensitive_patterns = self.config.get('sensitive_patterns', [])
        
        if format_type == 'json':
            return JsonFormatter(sensitive_patterns)
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def _setup_newrelic(self):
        """Setup New Relic integration (only initializes once per process)"""
        # Skip if already initialized to avoid redundant initialization per-module
        if AppLogger._newrelic_initialized:
            return
        
        try:
            import newrelic.agent
            
            # Check if agent is already initialized (e.g., by app.py or config file)
            if newrelic.agent.global_settings().license_key:
                AppLogger._newrelic_initialized = True
                return
            
            # Initialize New Relic agent
            app_name = self.config.get('newrelic', {}).get('app_name', self.app_name or 'asaad-app')
            license_key = self.config.get('newrelic', {}).get('license_key')
            
            if license_key:
                newrelic.agent.initialize(app_name=app_name, license_key=license_key)
                AppLogger._newrelic_initialized = True
                self.info("New Relic agent initialized by shared logger", app_name=app_name)
        except ImportError:
            self.warning("New Relic enabled but newrelic package not installed")
        except Exception as e:
            self.warning("Failed to initialize New Relic", error=str(e))
    
    def _build_log_data(self, message: str, **kwargs) -> Dict[str, Any]:
        """Build structured log data"""
        data = {
            'message': message,
        }
        
        # Add persistent context from initialization
        if self.config.get('include_context', True):
            data.update(self.context)
        
        # Add app name if available
        if self.app_name:
            data['app_name'] = self.app_name
        
        # Add call-specific data
        data.update(kwargs)
        
        return data
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method"""
        if not self.logger.isEnabledFor(level):
            return
        
        # Build structured data
        data = self._build_log_data(message, **kwargs)
        
        # Create log record with extra data
        if self.config.get('format') == 'json':
            # For JSON format, attach data to record
            extra = {'extra_data': data}
            self.logger.log(level, message, extra=extra)
        else:
            # For text format, just log the message
            self.logger.log(level, message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, 
              stack_trace: Optional[str] = None, **kwargs):
        """
        Log error message with optional exception and stack trace
        
        Args:
            message: Error description
            error: Exception object
            stack_trace: Stack trace string (use traceback.format_exc())
            **kwargs: Additional context
        """
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
        
        if stack_trace:
            kwargs['stack_trace'] = stack_trace
        
        self._log(logging.ERROR, message, **kwargs)
        
        # Record exception in New Relic if enabled
        if self.config.get('newrelic', {}).get('enabled', False) and error:
            try:
                import newrelic.agent
                newrelic.agent.record_exception()
            except:
                pass
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, message, **kwargs)


# Convenience function
def get_logger(name: str, app_name: Optional[str] = None, **context):
    """
    Get logger instance
    
    Args:
        name: Logger name (usually __name__)
        app_name: Application name for app-level config
        **context: Additional context to include in all logs
    
    Returns:
        AppLogger instance
    
    Example:
        logger = get_logger(__name__, app_name='image_generator', environment='production')
        logger.info("Server started", port=5000)
    """
    return AppLogger.get_logger(name, app_name, **context)
