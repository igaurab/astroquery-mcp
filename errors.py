"""Error models for astroquery MCP server."""

from enum import Enum
from typing import Any
from dataclasses import dataclass, field


class ErrorCode(str, Enum):
    """Error codes for MCP responses."""

    # Validation errors (400-level)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    INVALID_QUERY = "INVALID_QUERY"
    MISSING_PARAMETER = "MISSING_PARAMETER"

    # Authentication errors (401-level)
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"

    # Not found errors (404-level)
    NOT_FOUND = "NOT_FOUND"
    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
    BIBCODE_NOT_FOUND = "BIBCODE_NOT_FOUND"
    CATALOG_NOT_FOUND = "CATALOG_NOT_FOUND"

    # Rate limit errors (429-level)
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"

    # Timeout errors (504-level)
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

    # Service errors (500-level)
    SERVICE_ERROR = "SERVICE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class MCPError(Exception):
    """Standardized error for MCP tool responses.

    This exception can be raised and also serialized to a dict for
    returning structured error information to the orchestrating agent.
    """

    code: ErrorCode
    message: str
    service: str
    recoverable: bool = True
    suggestion: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON response."""
        return {
            "error": True,
            "code": self.code.value,
            "message": self.message,
            "service": self.service,
            "recoverable": self.recoverable,
            "suggestion": self.suggestion,
            "details": self.details,
        }

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.service}: {self.message}"


def validation_error(
    message: str, service: str = "validation", **details: Any
) -> MCPError:
    """Create a validation error."""
    return MCPError(
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        service=service,
        recoverable=False,
        suggestion="Check input parameters and try again",
        details=details,
    )


def not_found_error(
    message: str,
    service: str,
    code: ErrorCode = ErrorCode.NOT_FOUND,
    **details: Any,
) -> MCPError:
    """Create a not found error."""
    return MCPError(
        code=code,
        message=message,
        service=service,
        recoverable=False,
        suggestion="Verify the identifier exists or try alternative search terms",
        details=details,
    )


def service_error(message: str, service: str, **details: Any) -> MCPError:
    """Create a service error."""
    return MCPError(
        code=ErrorCode.SERVICE_ERROR,
        message=message,
        service=service,
        recoverable=True,
        suggestion="The service may be temporarily unavailable. Try again later.",
        details=details,
    )
