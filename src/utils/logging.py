"""
Logging Configuration Module

Provides logging setup for the project.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[Path] = None,
    log_level: str = "INFO",
    console: bool = True
) -> logging.Logger:
    """
    Set up logging configuration.
    
    Parameters
    ----------
    log_file : Path, optional
        Path to log file (default: None, no file logging)
    log_level : str, optional
        Logging level (default: "INFO")
    console : bool, optional
        Enable console logging (default: True)
    
    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    # Convert log level string to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('residual_carbon')
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = 'residual_carbon') -> logging.Logger:
    """
    Get a logger instance.
    
    Parameters
    ----------
    name : str, optional
        Logger name (default: 'residual_carbon')
    
    Returns
    -------
    logging.Logger
        Logger instance
    """
    return logging.getLogger(name)

