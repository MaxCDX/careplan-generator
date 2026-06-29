"""Application-level exceptions for controlled API errors."""

from typing import Any

from fastapi import status


class BaseAppException(Exception):
    """Base exception for expected application errors."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "APP_ERROR"
    message = "An application error occurred."

    def __init__(
        self,
        *,
        message: str | None = None,
        code: str | None = None,
        detail: Any = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.detail = detail if detail is not None else {}
        self.status_code = status_code or self.status_code
        super().__init__(self.message)


class BadRequestError(BaseAppException):
    """Raised when client input cannot be processed."""

    def __init__(self, code: str, message: str, detail: dict | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=code,
            message=message,
            detail=detail,
        )


class ConflictError(BaseAppException):
    """Raised when a business rule blocks the request."""

    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "Request conflicts with existing data."


class NotFoundError(BaseAppException):
    """Raised when a requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "Resource not found."


class ServiceUnavailableError(BaseAppException):
    """Raised when a downstream service cannot accept work."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "SERVICE_UNAVAILABLE"
    message = "Service is temporarily unavailable."
