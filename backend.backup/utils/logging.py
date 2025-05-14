import logging
import traceback
from typing import Any, Dict, List, Optional, Union
from config import config

# Module-level variables to control logger initialization
_logger_initialized = False
logger = None

def setup_logger() -> logging.Logger:
    """
    Configure and return the application logger.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    global _logger_initialized, logger
    
    # If logger is already initialized, return it
    if _logger_initialized:
        return logger
        
    _logger_initialized = True
    
    logger = logging.getLogger("app")
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    # Clear existing handlers to avoid duplication
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
    logger.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    
    return logger

# Ensure logger is initialized
logger = setup_logger()

# Monkey patch the info, debug, warning, error methods to prevent duplicate logs
_original_info = logger.info
_original_debug = logger.debug
_original_warning = logger.warning
_original_error = logger.error

# Last message cache to prevent exact duplicate messages in sequence
_last_log_message = None

def _deduplicating_log(original_func, message, *args, **kwargs):
    """Wrapper to prevent duplicate consecutive log messages"""
    global _last_log_message
    
    # Only log if this isn't the same as the last message
    if message != _last_log_message:
        _last_log_message = message
        return original_func(message, *args, **kwargs)
    
    # Otherwise skip to avoid duplication
    return None

# Replace logging methods with deduplicating versions
logger.info = lambda message, *args, **kwargs: _deduplicating_log(_original_info, message, *args, **kwargs)
logger.debug = lambda message, *args, **kwargs: _deduplicating_log(_original_debug, message, *args, **kwargs)
logger.warning = lambda message, *args, **kwargs: _deduplicating_log(_original_warning, message, *args, **kwargs)
logger.error = lambda message, *args, **kwargs: _deduplicating_log(_original_error, message, *args, **kwargs)

def log_separator(length: int = 80, char: str = "-") -> None:
    """
    Log a separator line for better visual distinction between processing phases.
    
    Args:
        length: Length of the separator line
        char: Character to use for the separator
    """
    logger.info(char * length)

def log_phase_header(phase_name: str, length: int = 80) -> None:
    """
    Log a formatted header for a processing phase.
    
    Args:
        phase_name: Name of the phase
        length: Length of the separator lines
    """
    log_separator(length, "=")
    logger.info(f" PHASE: {phase_name.upper()} ".center(length, "*"))
    log_separator(length, "=")

def log_section_header(section_name: str, length: int = 80) -> None:
    """
    Log a formatted header for a processing section.
    
    Args:
        section_name: Name of the section
        length: Length of the separator lines
    """
    log_separator(length)
    logger.info(f" {section_name} ".center(length, "-"))
    log_separator(length)

def safe_dump_for_log(obj: Any, max_len: int = 1000) -> str:
    """
    Safely convert an object to string for logging, with length limit.
    
    Args:
        obj: Any Python object to log
        max_len: Maximum string length to log
        
    Returns:
        str: String representation of the object
    """
    try:
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            result = str(obj)
        elif isinstance(obj, (list, tuple)):
            result = f"[List with {len(obj)} items] " + str(obj)
        elif isinstance(obj, dict):
            result = f"[Dict with {len(obj)} keys] " + str(obj)
        else:
            result = f"[Object of type {type(obj).__name__}] " + str(obj)
            
        if len(result) > max_len:
            return result[:max_len] + "... [truncated]"
        return result
    except Exception as e:
        return f"[Error dumping object: {str(e)}]"

def debug_dump(prefix: str, obj: Any) -> None:
    """
    Dump an object to log if debug is enabled.
    
    Args:
        prefix: Label for the dump
        obj: The object to dump
    """
    if config.DEBUG_LLM_IO:
        try:
            logger.debug(f"{prefix}: {safe_dump_for_log(obj, max_len=5000)}")
        except Exception as e:
            logger.debug(f"Error dumping {prefix}: {str(e)}")

def log_exception(e: Exception) -> None:
    """
    Log an exception with traceback.
    
    Args:
        e: The exception to log
    """
    log_separator(80, "!")
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    log_separator(80, "!") 