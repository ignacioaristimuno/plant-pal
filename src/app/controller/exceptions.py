"""Custom exceptions for the PlantPal API."""

from typing import Any, Dict, Optional


class PlantPalAPIException(Exception):
    """
    Base exception class for PlantPal API.

    All custom exceptions in the API should inherit from this base class
    to provide consistent error handling and logging capabilities.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional error details (optional)
            error_code: Machine-readable error code (optional)
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code

    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ValidationException(PlantPalAPIException):
    """Exception raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize validation exception.

        Args:
            message: Human-readable error message
            field: Name of the field that failed validation (optional)
            value: Value that failed validation (optional)
            details: Additional error details (optional)
        """
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = value

        super().__init__(
            message=message, details=error_details, error_code="VALIDATION_ERROR"
        )
        self.field = field
        self.value = value


class NonValidMessageException(ValidationException):
    """Exception raised when a user message is not valid."""

    def __init__(self, message: str, user_message: Optional[str] = None) -> None:
        """
        Initialize invalid message exception.

        Args:
            message: Human-readable error message
            user_message: The invalid user message (optional)
        """
        super().__init__(
            message=message,
            field="user_message",
            value=user_message,
            details={"reason": "invalid_content"},
        )


class NonValidSessionException(ValidationException):
    """Exception raised when a session identifier is not valid."""

    def __init__(self, message: str, session_id: Optional[str] = None) -> None:
        """
        Initialize invalid session exception.

        Args:
            message: Human-readable error message
            session_id: The invalid session ID (optional)
        """
        super().__init__(
            message=message,
            field="session_id",
            value=session_id,
            details={"reason": "invalid_session"},
        )


class WorkflowExecutionException(PlantPalAPIException):
    """Exception raised when workflow execution fails."""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        workflow_error: Optional[Exception] = None,
    ) -> None:
        """
        Initialize workflow execution exception.

        Args:
            message: Human-readable error message
            session_id: Session ID where the error occurred (optional)
            workflow_error: Original workflow exception (optional)
        """
        details = {}
        if session_id:
            details["session_id"] = session_id
        if workflow_error:
            details["original_error"] = str(workflow_error)
            details["error_type"] = type(workflow_error).__name__

        super().__init__(
            message=message, details=details, error_code="WORKFLOW_EXECUTION_ERROR"
        )
        self.session_id = session_id
        self.workflow_error = workflow_error
