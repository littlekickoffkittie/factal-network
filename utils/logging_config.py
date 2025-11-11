"""
Enhanced logging configuration for FractalChain.
Provides structured logging with rotation and multiple handlers.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON formatted string
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.

        Args:
            record: Log record

        Returns:
            Colored formatted string
        """
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    json_format: bool = False,
    colored_console: bool = True
) -> None:
    """
    Setup comprehensive logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for no file logging)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        json_format: Use JSON format for file logging
        colored_console: Use colored output for console
    """
    # Convert log level string to constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if colored_console and sys.stdout.isatty():
        console_format = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler (if log file specified)
    if log_file:
        # Create log directory if needed
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )

        file_handler.setLevel(numeric_level)

        if json_format:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s - '
                '[%(filename)s:%(lineno)d]',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Log startup message
    root_logger.info("="  * 60)
    root_logger.info("FractalChain logging initialized")
    root_logger.info(f"Log level: {log_level}")
    if log_file:
        root_logger.info(f"Log file: {log_file}")
    root_logger.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance with given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter for adding context to log messages."""

    def process(self, msg, kwargs):
        """Add extra context to log messages."""
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        kwargs['extra'].update(self.extra)
        return msg, kwargs


def get_context_logger(name: str, **context) -> LoggerAdapter:
    """
    Get logger with context fields.

    Args:
        name: Logger name
        **context: Context fields to include in all log messages

    Returns:
        LoggerAdapter with context
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context)
