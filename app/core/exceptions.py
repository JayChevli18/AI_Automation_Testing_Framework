"""Custom application exceptions."""


class AppError(Exception):
    """Base app exception."""


class StorageError(AppError):
    """Raised when storage operations fail."""


class NotFoundError(AppError):
    """Raised when required resources are missing."""


class ConflictError(AppError):
    """Raised when the request conflicts with current resource state (e.g. run in progress)."""

