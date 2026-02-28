"""
Auth-service exceptions. Map to HTTP in main via exception handlers.
Base types from code_shared; auth-specific ones here.
"""

from code_shared.core.exceptions import (
    ConflictError,
    UnauthorizedError,
)


class UsernameAlreadyRegisteredError(ConflictError):
    """Username is already taken (register)."""

    def __init__(self, message: str = "Username already registered") -> None:
        super().__init__(message)


class InvalidCredentialsError(UnauthorizedError):
    """Wrong password, invalid token, or user not found for token (login / me)."""

    def __init__(self, message: str = "Incorrect username or password") -> None:
        super().__init__(message)


class InvalidTokenError(UnauthorizedError):
    """JWT invalid or could not validate (e.g. /me)."""

    def __init__(self, message: str = "Could not validate credentials") -> None:
        super().__init__(message)
