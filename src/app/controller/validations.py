"""Validations for the PlantPal API."""

import re
from typing import Optional

from src.settings.logger import custom_logger


# Initialize logger
logger = custom_logger("Validations Controller")

# Compilation of regex patterns for performance
HARMFUL_PATTERNS = [
    re.compile(r"<script.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
    re.compile(r"<iframe.*?</iframe>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<object.*?</object>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<embed.*?>", re.IGNORECASE),
    re.compile(r"vbscript:", re.IGNORECASE),
    re.compile(r"data:text/html", re.IGNORECASE),
]

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    re.compile(
        r"\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b",
        re.IGNORECASE,
    ),
    re.compile(r'[;\'"]+', re.IGNORECASE),
    re.compile(r"--", re.IGNORECASE),
    re.compile(r"/\*.*?\*/", re.IGNORECASE | re.DOTALL),
]


def is_valid_message(message: Optional[str]) -> dict[str, bool]:
    """
    Validate if a user message is safe and appropriate for processing.

    This function performs comprehensive validation including:
    - Basic format validation (not empty, reasonable length)
    - Security validation (XSS, SQL injection prevention)
    - Content validation (inappropriate content detection)

    Args:
        message: The user message to validate

    Returns:
        bool: True if the message is valid and safe, False otherwise
    """
    if not message:
        logger.debug("Message validation failed: empty message")
        return {"is_valid": False, "message": "Message is required"}

    # Strip whitespace for validation
    cleaned_message = message.strip()

    # Check if message is empty after stripping
    if not cleaned_message:
        logger.debug("Message validation failed: empty message after stripping")
        return {"is_valid": False, "message": "Message is required"}

    # Check message length (reasonable bounds)
    if len(cleaned_message) > 2000:
        logger.warning(
            f"Message validation failed: message too long ({len(cleaned_message)} chars)"
        )
        return {"is_valid": False, "message": "Message is too long"}

    if len(cleaned_message) < 1:
        logger.debug("Message validation failed: message too short")
        return {"is_valid": False, "message": "Message is too short"}

    # Security validation - check for XSS attempts
    xss_check = _contains_xss_patterns(cleaned_message)
    if not xss_check["is_valid"]:
        logger.warning("Message validation failed: potential XSS content detected")
        return {
            "is_valid": False,
            "message": "Message contains potential XSS content",
        }

    # Security validation - check for SQL injection attempts
    sql_check = _contains_sql_injection_patterns(cleaned_message)
    if not sql_check["is_valid"]:
        logger.warning("Message validation failed: potential SQL injection detected")
        return {
            "is_valid": False,
            "message": "Message contains potential SQL injection",
        }

    logger.debug("Message validation passed")
    return {"is_valid": True, "message": "Message is valid"}


def is_valid_session_id(session_id: Optional[str]) -> dict[str, bool]:
    """
    Validate if a session ID is properly formatted and safe.

    Args:
        session_id: The session ID to validate

    Returns:
        bool: True if the session ID is valid, False otherwise
    """
    if not session_id:
        logger.debug("Session ID validation failed: empty session ID")
        return {"is_valid": False, "message": "Session ID is required"}

    # Strip whitespace
    cleaned_session_id = session_id.strip()

    # Check if empty after stripping
    if not cleaned_session_id:
        logger.debug("Session ID validation failed: empty after stripping")
        return {"is_valid": False, "message": "Session ID is required"}

    # Check length bounds
    if len(cleaned_session_id) < 3 or len(cleaned_session_id) > 100:
        logger.warning(
            f"Session ID validation failed: invalid length ({len(cleaned_session_id)})"
        )
        return {"is_valid": False, "message": "Session ID is invalid"}

    # Check for allowed characters (alphanumeric, underscore, hyphen)
    if not re.match(r"^[a-zA-Z0-9_-]+$", cleaned_session_id):
        logger.warning("Session ID validation failed: contains invalid characters")
        return {"is_valid": False, "message": "Session ID is invalid"}

    logger.debug("Session ID validation passed")
    return {"is_valid": True, "message": "Session ID is valid"}


def _contains_xss_patterns(message: str) -> dict[str, bool]:
    """
    Check if message contains potential XSS patterns.

    Args:
        message: Message to check

    Returns:
        dict[str, bool]: True if XSS patterns detected, False otherwise
    """
    for pattern in HARMFUL_PATTERNS:
        if pattern.search(message):
            return {
                "is_valid": False,
                "message": "Message contains potential XSS content",
            }
    return {"is_valid": True, "message": "Message is valid"}


def _contains_sql_injection_patterns(message: str) -> dict[str, bool]:
    """
    Check if message contains potential SQL injection patterns.

    Args:
        message: Message to check

    Returns:
        dict[str, bool]: True if SQL injection patterns detected, False otherwise
    """
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(message):
            return {
                "is_valid": False,
                "message": "Message contains potential SQL injection",
            }
    return {"is_valid": True, "message": "Message is valid"}


def sanitize_message(message: str) -> str:
    """
    Sanitize user message by removing potentially harmful content.

    Args:
        message: Message to sanitize

    Returns:
        str: Sanitized message
    """
    if not message:
        return ""

    # Strip whitespace
    sanitized = message.strip()

    # Remove potential HTML tags
    sanitized = re.sub(r"<[^>]+>", "", sanitized)

    # Remove potential script content
    for pattern in HARMFUL_PATTERNS:
        sanitized = pattern.sub("", sanitized)

    # Normalize whitespace
    sanitized = re.sub(r"\s+", " ", sanitized)

    return sanitized.strip()
