from __future__ import annotations

import asyncio
from typing import Any, cast

import httpx
import pytest

from py_understat import (
    InvalidIdentifierError,
    League,
    ResourceNotFoundError,
    RetryPolicy,
    Season,
    UnderstatClient,
)


def _player_statistic() -> dict[str, str]:
    return {
        "id": "7",
        "player_name": "Ada Striker",
        "position": "F",
        "games": "1",
        "goals": "1",
        "shots": "2",
        "time": "90",
        "xG": "0.8",
        "assists": "0",
        "xA": "0.1",
        "key_passes": "1",
        "npg": "1",
        "npxG": "0.8",
        "xGChain": "1.2",
        "xGBuildup": "0.2",
    }


def _match() -> dict[str, Any]:
    return {
        "id": "9",
        "isResult": True,
        "h": {"id": "1", "title": "Home", "short_title": "HOM"},
        "a": {"id": "2", "title": "Away", "short_title": "AWY"},
        "goals": {"h": "2", "a": "1"},
        "xG": {"h": "1.2", "a": "0.9"},
        "datetime": "2025-08-15 19:00:00",
        "forecast": {"w": "0.5", "d": "0.2", "l": "0.3"},
    }


def _shot() -> dict[str, str]:
    return {
        "id": "42",
        "minute": "35",
        "result": "Goal",
        "X": "0.8",
        "Y": "0.6",
        "xG": "0.4",
        "player": "Ada Striker",
        "h_a": "h",
        "player_id": "7",
        "situation": "OpenPlay",
        "season": "2025",
        "shotType": "RightFoot",
        "match_id": "9",
        "h_team": "Home",
        "a_team": "Away",
        "date": "2025-08-15 19:35:00",
    }


def _payloads() -> dict[str, dict[str, Any]]:
    player_statistic = _player_statistic()
    match = _match()
    shot = _shot()
    upcoming_match = {
        "id": "32255",
        "isResult": False,
        "h": {"id": "1", "title": "Home", "short_title": "HOM"},
        "a": {"id": "2", "title": "Away", "short_title": "AWY"},
        "goals": {"h": None, "a": None},
        "xG": {"h": None, "a": None},
        "datetime": "2026-09-04 18:30:00",
    }
    return {
        "/getLeagueData/EPL/2025": {
            "teams": {"1": {"id": "1", "title": "Home", "history": []}},
            "players": [player_statistic],
            "dates": [match, upcoming_match],
        },
        "/getTeamData/Home/2025": {
            "players": [player_statistic],
            "dates": [match],
            "statistics": {
                "situation": {
                    "OpenPlay": {
                        "shots": "2",
                        "goals": "1",
                        "xG": "0.8",
                        "against": {"shots": "1", "goals": "0", "xG": "0.2"},
                    }
                }
            },
        },
        "/getPlayerData/7": {
            "player": {"id": "7", "name": "Ada Striker", "favorite_position": "FW"},
            "matches": [
                {
                    "id": "9",
                    "season": "2025",
                    "date": "2025-08-15",
                    "position": "FW",
                    "goals": "1",
                    "shots": "2",
                    "time": "90",
                    "xG": "0.8",
                    "assists": "0",
                    "xA": "0.1",
                    "key_passes": "1",
                    "npg": "1",
                    "npxG": "0.8",
                    "xGChain": "1.2",
                    "xGBuildup": "0.2",
                    "h_team": "Home",
                    "a_team": "Away",
                }
            ],
            "groups": {},
            "shots": [shot],
            "positionsList": ["FW"],
        },
        "/getMatchData/9": {
            "rosters": {
                "h": {
                    "7": {
                        "id": "7",
                        "player_id": "7",
                        "team_id": "1",
                        "player": "Ada Striker",
                        "position": "FW",
                        "time": "90",
                        "goals": "1",
                        "xG": "0.8",
                        "assists": "0",
                        "xA": "0.1",
                    }
                }
            },
            "shots": {"h": [shot]},
            "tmpl": {},
        },
    }


def test_all_resources_use_ajax_and_normalize_models() -> None:
    payloads = _payloads()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Requested-With"] == "XMLHttpRequest"
        assert request.headers["User-Agent"].startswith("py-understat/")
        assert request.headers["User-Agent"].endswith(
            "(+https://github.com/buenavista62/py-understat)"
        )
        return httpx.Response(200, json=payloads[request.url.path])

    async def exercise() -> None:
        async with UnderstatClient(transport=httpx.MockTransport(handler)) as client:
            league = await client.league(League.EPL).get("2025/2026")
            team = await client.team("Home").get(Season("2025/2026"))
            player = await client.player(7).get()
            match = await client.match(9).get()

        assert league.players[0].expected_goals == 0.8
        assert league.matches[0].goals.home == 2
        assert league.matches[1].is_result is False
        assert league.matches[1].goals.home is None
        assert league.matches[1].expected_goals.away is None
        assert league.matches[1].forecast is None
        assert team.statistics["situation"]["OpenPlay"].expected_goals == 0.8
        assert player.shots[0].expected_goals == 0.4
        assert match.shots["h"][0].expected_goals == 0.4

    asyncio.run(exercise())


def test_retry_policy_retries_rate_limits_and_honors_retry_after() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=_payloads()["/getLeagueData/EPL/2025"])

    async def exercise() -> None:
        async with UnderstatClient(
            transport=httpx.MockTransport(handler),
            retry_policy=RetryPolicy(max_attempts=2, initial_delay=0, max_delay=0),
        ) as client:
            await client.league(League.EPL).get("2025/2026")

    asyncio.run(exercise())
    assert attempts == 2


def test_client_raises_resource_not_found() -> None:
    async def exercise() -> None:
        async with UnderstatClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(404)),
        ) as client:
            with pytest.raises(ResourceNotFoundError):
                await client.player(7).get()

    asyncio.run(exercise())


@pytest.mark.parametrize("value", ["2025", "2025/2027", "2013/2014"])
def test_season_rejects_invalid_labels(value: str) -> None:
    with pytest.raises(InvalidIdentifierError):
        Season(value)


@pytest.mark.parametrize("identifier", [0, -1, True, "7"])
def test_resource_identifiers_must_be_positive_integers(identifier: object) -> None:
    with pytest.raises(InvalidIdentifierError):
        UnderstatClient().player(cast(int, identifier))
