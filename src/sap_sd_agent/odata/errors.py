from __future__ import annotations


class SapODataError(RuntimeError):
    """Base exception for SAP OData failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class SapConnectionError(SapODataError):
    """Raised when SAP cannot be reached."""


class SapAuthenticationError(SapODataError):
    """Raised when SAP rejects the configured credentials."""


class SapNotFoundError(SapODataError):
    """Raised when the requested SAP entity does not exist."""
