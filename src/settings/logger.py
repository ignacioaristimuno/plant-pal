from logging import DEBUG, Formatter, Logger, StreamHandler, getLogger
import sys


def custom_logger(logger_name: str) -> Logger:
    """
    Create and configure a logger with a specified name.

    This function initializes a logger with the given name, sets its logging level
    to DEBUG, and configures a StreamHandler with a specific format for log messages.
    If the logger does not already have handlers, a new StreamHandler is added.
    The logger's propagation is enabled to allow logs to be passed to parent loggers (like LangGraph's).

    Args:
        logger_name (str): The name to assign to the logger.

    Returns:
        Logger: A configured logger instance with the specified name.
    """

    logger = getLogger(f" {logger_name} - ")
    logger.setLevel(DEBUG)
    
    # Force handler creation even if handlers exist to ensure Docker compatibility
    console_handler = StreamHandler(sys.stdout)
    console_handler.setLevel(DEBUG)
    formatter = Formatter(
        "%(asctime)s - %(name)s%(levelname)s: %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S%p",
    )
    console_handler.setFormatter(formatter)
    
    # Clear existing handlers and add new one for Docker
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.propagate = False  # Disable propagation for Docker to avoid duplicate logs
    return logger
