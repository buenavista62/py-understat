"""The asynchronous client and resource query API."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Self, TypeVar
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from .exceptions import (
    InvalidIdentifierError,
    PayloadValidationError,
    RateLimitError,
    ResourceNotFoundError,
    UpstreamError,
)
from .models import LeagueSnapshot, MatchSnapshot, PlayerSnapshot, TeamSnapshot

_BASE_URL = "https://understat.com/"
_AJAX_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}
_SEASON_PATTERN = re.compile(r"(?P<start>\d{4})/(?P<end>\d{4})")
_Snapshot = TypeVar(
    "_Snapshot", LeagueSnapshot, TeamSnapshot, PlayerSnapshot, MatchSnapshot
)


def _package_version() -> str:
    try:
        return version("py-understat")
    except PackageNotFoundError:
        return "development"


class League(StrEnum):
    """The competitions available through Understat."""

    EPL = "EPL"
    LA_LIGA = "La_Liga"
    BUNDESLIGA = "Bundesliga"
    SERIE_A = "Serie_A"
    LIGUE_1 = "Ligue_1"
    RFPL = "RFPL"


@dataclass(frozen=True, slots=True, init=False)
class Season:
    """A competition season represented as ``YYYY/YYYY+1``."""

    start_year: int

    def __init__(self, value: str) -> None:
        match = _SEASON_PATTERN.fullmatch(value)
        if match is None:
            raise InvalidIdentifierError("season must use the YYYY/YYYY+1 format")

        start_year = int(match["start"])
        if int(match["end"]) != start_year + 1:
            raise InvalidIdentifierError("season must end in the year after it starts")
        if start_year < 2014:
            raise InvalidIdentifierError(
                "Understat data starts with the 2014/2015 season"
            )
        object.__setattr__(self, "start_year", start_year)

    @property
    def label(self) -> str:
        """The public season label."""
        return f"{self.start_year}/{self.start_year + 1}"

    def __str__(self) -> str:
        return self.label


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry configuration for transient, idempotent GET requests."""

    max_attempts: int = 3
    initial_delay: float = 0.25
    max_delay: float = 4.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.initial_delay < 0 or self.max_delay < 0:
            raise ValueError("retry delays cannot be negative")


_DEFAULT_RETRY_POLICY = RetryPolicy()


class UnderstatClient:
    """Own an asynchronous HTTP client for querying Understat data.

    Use as an async context manager to deterministically release HTTP resources.
    """

    def __init__(
        self,
        *,
        timeout: float | httpx.Timeout | None = 20.0,
        retry_policy: RetryPolicy | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._retry_policy = retry_policy or _DEFAULT_RETRY_POLICY
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            follow_redirects=True,
            headers={
                **_AJAX_HEADERS,
                "User-Agent": f"py-understat/{_package_version()} (+https://github.com/buenavista62/py-understat)",
            },
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying :class:`httpx.AsyncClient`."""
        await self._http.aclose()

    def league(self, league: League) -> _LeagueResource:
        """Select a League resource."""
        if not isinstance(league, League):
            raise InvalidIdentifierError("league must be a League enum member")
        return _LeagueResource(self, league)

    def team(self, handle: str) -> _TeamResource:
        """Select a Team resource by its exact Understat handle."""
        _validate_team_handle(handle)
        return _TeamResource(self, handle)

    def player(self, player_id: int) -> _PlayerResource:
        """Select a Player resource by its positive Understat ID."""
        return _PlayerResource(self, _validate_id(player_id, "player_id"))

    def match(self, match_id: int) -> _MatchResource:
        """Select a Match resource by its positive Understat ID."""
        return _MatchResource(self, _validate_id(match_id, "match_id"))

    async def _get_snapshot(self, path: str, model: type[_Snapshot]) -> _Snapshot:
        payload = await self._get_json(path)
        try:
            return model.model_validate(payload)
        except ValidationError as error:
            raise PayloadValidationError(
                f"Understat returned an incompatible {model.__name__} payload"
            ) from error

    async def _get_json(self, path: str) -> dict[str, Any]:
        response: httpx.Response | None = None
        last_error: Exception | None = None

        for attempt in range(self._retry_policy.max_attempts):
            try:
                response = await self._http.get(path)
            except httpx.RequestError as error:
                last_error = error
                if attempt + 1 == self._retry_policy.max_attempts:
                    break
                await asyncio.sleep(self._backoff_delay(attempt))
                continue

            if response.status_code == 404:
                raise ResourceNotFoundError(
                    f"Understat has no resource at {response.request.url}"
                )
            if response.status_code == 429:
                last_error = _response_error(response)
                if attempt + 1 < self._retry_policy.max_attempts:
                    await asyncio.sleep(self._retry_delay(response, attempt))
                    continue
                raise RateLimitError(
                    "Understat rate-limited the request after retries"
                ) from last_error
            if response.status_code >= 500:
                last_error = _response_error(response)
                if attempt + 1 < self._retry_policy.max_attempts:
                    await asyncio.sleep(self._retry_delay(response, attempt))
                    continue
                break
            if response.is_error:
                raise UpstreamError(
                    f"Understat returned HTTP {response.status_code}"
                ) from _response_error(response)

            try:
                payload = response.json()
            except ValueError as error:
                raise PayloadValidationError(
                    "Understat returned a non-JSON response"
                ) from error
            if not isinstance(payload, dict):
                raise PayloadValidationError(
                    "Understat returned a JSON payload other than an object"
                )
            return payload

        raise UpstreamError(
            "Understat could not fulfill the request after retries"
        ) from last_error

    def _backoff_delay(self, attempt: int) -> float:
        return min(
            self._retry_policy.initial_delay * (2**attempt),
            self._retry_policy.max_delay,
        )

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            return self._backoff_delay(attempt)
        try:
            return min(float(retry_after), self._retry_policy.max_delay)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
            except (TypeError, ValueError):
                return self._backoff_delay(attempt)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return min(
                max(0.0, (retry_at - datetime.now(UTC)).total_seconds()),
                self._retry_policy.max_delay,
            )


@dataclass(frozen=True, slots=True)
class _LeagueResource:
    client: UnderstatClient
    league: League

    async def get(self, season: Season | str) -> LeagueSnapshot:
        """Retrieve the League snapshot for ``season``."""
        normalized_season = _as_season(season)
        return await self.client._get_snapshot(
            f"getLeagueData/{quote(self.league.value, safe='_')}/{normalized_season.start_year}",
            LeagueSnapshot,
        )


@dataclass(frozen=True, slots=True)
class _TeamResource:
    client: UnderstatClient
    handle: str

    async def get(self, season: Season | str) -> TeamSnapshot:
        """Retrieve the Team snapshot for ``season``."""
        normalized_season = _as_season(season)
        return await self.client._get_snapshot(
            f"getTeamData/{quote(self.handle, safe='_')}/{normalized_season.start_year}",
            TeamSnapshot,
        )


@dataclass(frozen=True, slots=True)
class _PlayerResource:
    client: UnderstatClient
    player_id: int

    async def get(self) -> PlayerSnapshot:
        """Retrieve the Player snapshot."""
        return await self.client._get_snapshot(
            f"getPlayerData/{self.player_id}", PlayerSnapshot
        )


@dataclass(frozen=True, slots=True)
class _MatchResource:
    client: UnderstatClient
    match_id: int

    async def get(self) -> MatchSnapshot:
        """Retrieve the Match snapshot."""
        return await self.client._get_snapshot(
            f"getMatchData/{self.match_id}", MatchSnapshot
        )


def _as_season(value: Season | str) -> Season:
    if isinstance(value, Season):
        return value
    if isinstance(value, str):
        return Season(value)
    raise InvalidIdentifierError("season must be a Season or YYYY/YYYY+1 string")


def _validate_team_handle(handle: str) -> None:
    if (
        not isinstance(handle, str)
        or not handle
        or handle != handle.strip()
        or "/" in handle
    ):
        raise InvalidIdentifierError(
            "team handle must be a non-empty, exact Understat URL handle"
        )


def _validate_id(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InvalidIdentifierError(f"{name} must be a positive integer")
    return value


def _response_error(response: httpx.Response) -> httpx.HTTPStatusError:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        return error
    raise RuntimeError("response was expected to be an error")
