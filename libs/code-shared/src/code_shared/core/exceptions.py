"""
Shared exceptions for the whole system.

Use these as base classes so services can map them to HTTP (or other transports)
in one place. No framework dependency.
"""


class AppError(Exception):
    """Base for application errors that can be mapped to HTTP or other responses."""

    def __init__(
        self,
        message: str = "An error occurred",
        *,
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BadRequestError(AppError):
    """Invalid input or malformed request (400)."""

    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message, status_code=400)


class UnauthorizedError(AppError):
    """Authentication required or invalid credentials (401)."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401)


class ForbiddenError(AppError):
    """Authenticated but not allowed to perform the action (403)."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403)


class NotFoundError(AppError):
    """Resource not found (404)."""

    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, status_code=404)


class ConflictError(AppError):
    """Conflict with current state (e.g. duplicate resource) (409)."""

    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, status_code=409)
