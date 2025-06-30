"""
Centralized logging configuration to prevent truncation and improve debugging
"""
import logging
import sys
from typing import Optional


def setup_application_logging(level: str = "INFO", force_flush: bool = True):
    """
    Setup application-wide logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        force_flush: Whether to force immediate flushing of stdout
    """
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True
    )
    
    # Set specific levels for noisy modules
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("azure.cosmos").setLevel(logging.WARNING) 
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Force stdout to flush immediately if requested
    if force_flush:
        sys.stdout.reconfigure(line_buffering=True)
    
    # Create a logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"🔧 Application logging configured at {level} level")
    
    return logger


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with consistent formatting
    
    Args:
        name: Logger name (usually __name__)
        level: Optional specific level for this logger
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    
    return logger


def flush_logs():
    """Force flush all log outputs"""
    sys.stdout.flush()
    sys.stderr.flush()


def log_startup_step(step: str, step_num: int, total_steps: int, logger: logging.Logger):
    """
    Log a startup step with consistent formatting
    
    Args:
        step: Description of the step
        step_num: Current step number
        total_steps: Total number of steps
        logger: Logger instance to use
    """
    logger.info(f"[{step_num}/{total_steps}] {step}")


def log_completion(message: str, logger: logging.Logger, success: bool = True):
    """
    Log completion with appropriate emoji and formatting
    
    Args:
        message: Completion message
        logger: Logger instance to use  
        success: Whether this was successful (affects emoji)
    """
    emoji = "✅" if success else "❌"
    logger.info(f"{emoji} {message}")
    flush_logs()


def log_error_with_context(error: Exception, context: str, logger: logging.Logger):
    """
    Log an error with additional context
    
    Args:
        error: The exception that occurred
        context: Additional context about where/when the error occurred
        logger: Logger instance to use
    """
    logger.error(f"❌ {context}: {str(error)}")
    logger.debug(f"Full error details: {error}", exc_info=True)
    flush_logs()
