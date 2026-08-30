"""Exceptions raised by :mod:`py_understat`."""

from __future__ import annotations


class UnderstatError(Exception):
    """Base class for all package-level failures."""


class InvalidIdentifierError(UnderstatError, ValueError):
    """A resource identifier or competition season is invalid locally."""


class ResourceNotFoundError(UnderstatError):
    """Understat has no resource for the requested identifier."""


class RateLimitError(UnderstatError):
    """Understat kept rate-limiting a request after retries."""


class UpstreamError(UnderstatError):
    """Understat or the network could not fulfill a request."""


class PayloadValidationError(UnderstatError):
    """Understat returned a payload incompatible with the public models."""
