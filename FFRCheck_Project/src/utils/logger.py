"""Logging utilities for FFRCheck"""

import logging
import sys
from pathlib import Path
from typing import Optional
from .config import get_config


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        """Format log record with color."""
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str = "FFRCheck",
    log_file: Optional[Path] = None,
    console_level: str = "INFO",
    file_level: str = "DEBUG"
) -> logging.Logger:
    """
    Setup logger with console and optional file output.
    
    Args:
        name: Logger name
        log_file: Optional path to log file
        console_level: Console logging level
        file_level: File logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Get configuration
    config = get_config()
    log_format = config.get('logging.format')
    date_format = config.get('logging.date_format')
    
    # Set logger level to lowest of console and file
    logger.setLevel(min(
        getattr(logging, console_level),
        getattr(logging, file_level)
    ))
    
    # Console handler with color
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level))
    console_formatter = ColoredFormatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if log_file provided
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, file_level))
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "FFRCheck") -> logging.Logger:
    """
    Get existing logger or create default one.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set it up with defaults
    if not logger.handlers:
        return setup_logger(name)
    
    return logger
