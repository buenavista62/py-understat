"""An asynchronous, typed client for Understat football statistics."""

from .client import League, RetryPolicy, Season, UnderstatClient
from .exceptions import (
    InvalidIdentifierError,
    PayloadValidationError,
    RateLimitError,
    ResourceNotFoundError,
    UnderstatError,
    UpstreamError,
)
from .models import (
    LeagueSnapshot,
    MatchSnapshot,
    PlayerSnapshot,
    TeamSnapshot,
)

__all__ = [
    "InvalidIdentifierError",
    "League",
    "LeagueSnapshot",
    "MatchSnapshot",
    "PayloadValidationError",
    "PlayerSnapshot",
    "RateLimitError",
    "ResourceNotFoundError",
    "RetryPolicy",
    "Season",
    "TeamSnapshot",
    "UnderstatClient",
    "UnderstatError",
    "UpstreamError",
]

__version__ = "0.1.3"
