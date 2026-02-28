"""
Shared core utilities.

Keep this package `__init__` lightweight: do not import optional/heavy deps at
import time (e.g. llama-index, weaviate). Import those from submodules.
"""

from code_shared.core.exceptions import (  # re-export, lightweight
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)

__all__ = [
    "AppError",
    "BadRequestError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "UnauthorizedError",
]
