"""Centralized logging configuration for the agentic neurodata conversion system.

This module provides structured logging with proper formatters, handlers, and configuration
that supports both development and production environments. It integrates with the settings
system and provides context-aware logging for MCP server operations, agent interactions,
and conversion workflows.
"""

import logging
import logging.config
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager

from .exceptions import AgenticConverterError


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs for production environments."""
    
    def __init__(self, include_extra: bool = True):
        """Initialize structured formatter.
        
        Args:
            include_extra: Whether to include extra fields from log records
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                }:
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        # Handle AgenticConverterError specially
        if record.exc_info and isinstance(record.exc_info[1], AgenticConverterError):
            error = record.exc_info[1]
            log_entry["error_details"] = error.to_dict()
        
        return json.dumps(log_entry, default=str)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development environments."""
    
    def __init__(self):
        """Initialize development formatter with colors and readable format."""
        super().__init__()
        
        # Color codes for different log levels
        self.colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'      # Reset
        }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and readable structure."""
        # Get color for log level
        color = self.colors.get(record.levelname, '')
        reset = self.colors['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # Format basic message
        formatted = f"{color}[{timestamp}] {record.levelname:8} {record.name:20} {reset}{record.getMessage()}"
        
        # Add location info for debug level
        if record.levelno <= logging.DEBUG:
            formatted += f" ({record.filename}:{record.lineno})"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        # Add extra context if available
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            } and not key.startswith('_'):
                extra_fields[key] = value
        
        if extra_fields:
            formatted += f"\n  Context: {extra_fields}"
        
        return formatted


class LoggingConfig:
    """Configuration class for logging setup."""
    
    def __init__(
        self,
        level: str = "INFO",
        format_type: str = "development",
        log_file: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_console: bool = True,
        logger_levels: Optional[Dict[str, str]] = None
    ):
        """Initialize logging configuration.
        
        Args:
            level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_type: Formatter type ('development' or 'structured')
            log_file: Path to log file (optional)
            max_file_size: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
            enable_console: Whether to enable console logging
            logger_levels: Specific log levels for different loggers
        """
        self.level = level.upper()
        self.format_type = format_type
        self.log_file = log_file
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.logger_levels = logger_levels or {}


def setup_logging(config: Optional[LoggingConfig] = None) -> None:
    """Set up centralized logging configuration.
    
    Args:
        config: Logging configuration object. If None, uses default development config.
    """
    if config is None:
        config = LoggingConfig()
    
    # Create formatters
    if config.format_type == "structured":
        formatter = StructuredFormatter()
    else:
        formatter = DevelopmentFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if config.enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, config.level))
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if config.log_file:
        from logging.handlers import RotatingFileHandler
        
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            config.log_file,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, config.level))
        root_logger.addHandler(file_handler)
    
    # Configure specific logger levels
    for logger_name, level in config.logger_levels.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper()))
    
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


@contextmanager
def log_context(**kwargs):
    """Context manager for adding structured context to log messages.
    
    Usage:
        with log_context(agent_name="conversion", operation="generate_script"):
            logger.info("Starting conversion")  # Will include context
    
    Args:
        **kwargs: Context key-value pairs to add to log messages
    """
    # Get the logger from the calling frame
    import inspect
    frame = inspect.currentframe().f_back
    logger_name = frame.f_globals.get('__name__', 'unknown')
    logger = get_logger(logger_name)
    
    # Store original logger class
    original_class = logger.__class__
    
    class ContextLogger(original_class):
        def _log(self, level, msg, args, **log_kwargs):
            # Add context to extra
            extra = log_kwargs.get('extra', {})
            extra.update(kwargs)
            log_kwargs['extra'] = extra
            super()._log(level, msg, args, **log_kwargs)
    
    # Temporarily replace logger class
    logger.__class__ = ContextLogger
    
    try:
        yield logger
    finally:
        # Restore original logger class
        logger.__class__ = original_class


def log_function_call(logger: Optional[logging.Logger] = None):
    """Decorator to automatically log function calls with parameters and results.
    
    Args:
        logger: Logger to use. If None, creates logger from function module.
    
    Usage:
        @log_function_call()
        def my_function(param1, param2):
            return "result"
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            # Log function entry
            logger.debug(
                f"Calling {func.__name__}",
                extra={
                    'function': func.__name__,
                    'function_args': str(args) if args else None,
                    'function_kwargs': kwargs if kwargs else None
                }
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful completion
                logger.debug(
                    f"Completed {func.__name__}",
                    extra={
                        'function': func.__name__,
                        'result_type': type(result).__name__
                    }
                )
                
                return result
            
            except Exception as e:
                # Log exception
                logger.error(
                    f"Error in {func.__name__}: {e}",
                    exc_info=True,
                    extra={
                        'function': func.__name__,
                        'error_type': type(e).__name__
                    }
                )
                raise
        
        return wrapper
    return decorator


# Pre-configured logging setups for common scenarios
def setup_development_logging(level: str = "DEBUG") -> None:
    """Set up logging optimized for development with readable console output."""
    config = LoggingConfig(
        level=level,
        format_type="development",
        enable_console=True,
        logger_levels={
            "agentic_neurodata_conversion": level,
            "uvicorn": "INFO",
            "fastapi": "INFO"
        }
    )
    setup_logging(config)


def setup_production_logging(
    level: str = "INFO",
    log_file: str = "logs/agentic_converter.log"
) -> None:
    """Set up logging optimized for production with structured JSON output."""
    config = LoggingConfig(
        level=level,
        format_type="structured",
        log_file=log_file,
        enable_console=True,
        logger_levels={
            "agentic_neurodata_conversion": level,
            "uvicorn": "WARNING",
            "fastapi": "WARNING"
        }
    )
    setup_logging(config)


def setup_testing_logging() -> None:
    """Set up minimal logging for testing environments."""
    config = LoggingConfig(
        level="WARNING",
        format_type="development",
        enable_console=False,
        logger_levels={
            "agentic_neurodata_conversion": "WARNING"
        }
    )
    setup_logging(config)


def setup_logging_from_settings(settings_instance=None) -> None:
    """Set up logging based on application settings.
    
    Args:
        settings_instance: Settings instance to use. If None, imports and uses global settings.
    """
    if settings_instance is None:
        from .config import settings
        settings_instance = settings
    
    log_config = settings_instance.get_log_config()
    
    # Determine log file path based on environment
    log_file = None
    if settings_instance.environment == "production":
        log_file = "logs/agentic_converter.log"
    elif settings_instance.environment == "staging":
        log_file = "logs/agentic_converter_staging.log"
    # Development and testing don't use log files by default
    
    # Create logging configuration
    config = LoggingConfig(
        level=log_config["level"],
        format_type="structured" if log_config["format"] == "json" else "development",
        log_file=log_file,
        enable_console=True,
        logger_levels={
            "agentic_neurodata_conversion": log_config["level"],
            "uvicorn": "INFO" if settings_instance.debug else "WARNING",
            "fastapi": "INFO" if settings_instance.debug else "WARNING",
            "sqlalchemy": "INFO" if settings_instance.database.echo else "WARNING"
        }
    )
    
    setup_logging(config)
    
    # Log the configuration setup
    logger = get_logger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "environment": settings_instance.environment,
            "log_level": log_config["level"],
            "format_type": log_config["format"],
            "debug_mode": settings_instance.debug,
            "verbose_mode": settings_instance.verbose
        }
    )


# Export main functions
__all__ = [
    'LoggingConfig',
    'setup_logging',
    'get_logger',
    'log_context',
    'log_function_call',
    'setup_development_logging',
    'setup_production_logging', 
    'setup_testing_logging',
    'setup_logging_from_settings',
    'StructuredFormatter',
    'DevelopmentFormatter'
]