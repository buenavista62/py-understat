# py-understat

An asynchronous, typed client for football statistics published by [Understat](https://understat.com/). This is an unofficial client and is not affiliated with Understat.

![PyPI version](https://img.shields.io/pypi/v/py-understat.svg?cacheSeconds=300)
![Python versions](https://img.shields.io/pypi/pyversions/py-understat.svg?cacheSeconds=300)
![License](https://img.shields.io/github/license/buenavista62/py-understat.svg?cacheSeconds=300)
![CI](https://img.shields.io/github/actions/workflow/status/buenavista62/py-understat/ci.yml.svg?label=CI&cacheSeconds=300)
![GitHub release](https://img.shields.io/github/v/release/buenavista62/py-understat.svg?cacheSeconds=300)

## Features

- **Async first** — one `httpx.AsyncClient` owned by the client; use it as an async context manager.
- **Typed snapshots** — frozen Pydantic models with native Python values; unknown source fields stay readable via `extra`.
- **Resilient** — bounded exponential backoff for transport failures, `429`, and `5xx`; honors `Retry-After`.
- **Strict identifiers** — invalid leagues, seasons, team handles, and IDs fail locally before any request.
- **Zero magic** — no hidden caching or global rate limiting; you stay in control of immutable snapshots.

## Requirements

- Python **3.13 or newer** (the package is developed and tested against 3.13+)

## Install

```bash
uv add py-understat
# or
pip install py-understat
```

From a checkout, install the package and its development tools with:

```bash
uv sync --all-groups
```

## Quick start

```python
import asyncio

from py_understat import League, UnderstatClient


async def main() -> None:
    async with UnderstatClient() as client:
        premier_league = await client.league(League.EPL).get("2025/2026")

    top_scorer = max(premier_league.players, key=lambda player: player.goals)
    print(top_scorer.player_name, top_scorer.goals)


asyncio.run(main())
```

## Resources

Each `get()` call returns the complete snapshot Understat supplies for that resource:

| Resource | Query | Snapshot |
| --- | --- | --- |
| League | `client.league(League.BUNDESLIGA).get("2025/2026")` | `LeagueSnapshot` |
| Team | `client.team("Bayern_Munich").get("2025/2026")` | `TeamSnapshot` |
| Player | `client.player(8260).get()` | `PlayerSnapshot` |
| Match | `client.match(28778).get()` | `MatchSnapshot` |

```python
async with UnderstatClient() as client:
    league = await client.league(League.BUNDESLIGA).get("2025/2026")
    team = await client.team("Bayern_Munich").get("2025/2026")
    player = await client.player(8260).get()
    match = await client.match(28778).get()

league.players  # PlayerStatistic records
league.matches  # MatchRecord records
league.teams  # TeamSeason records keyed by Understat team ID
team.statistics  # Typed team statistic categories
player.matches  # PlayerMatch records
player.shots  # Shot records
match.rosters  # RosterEntry records grouped by home/away side
match.shots  # Shot records grouped by home/away side
```

## Identifiers

- `League` is an enum with Understat's six competitions: `EPL`, `LA_LIGA`, `BUNDESLIGA`, `SERIE_A`, `LIGUE_1`, `RFPL`.
- Team queries take the exact Understat team handle, such as `"Manchester_United"`.
- Player and Match queries take a positive Understat integer ID.
- League and Team queries take a competition season as `"YYYY/YYYY+1"`, for example `"2025/2026"`. Reuse a validated value with `Season("2025/2026")`; seasons before 2014/2015 are rejected (Understat data starts there).

Invalid identifiers fail locally with `InvalidIdentifierError` before any request is sent.

## Data and failures

Known fields are normalized to native Python values: IDs and counts become `int`, expected-goal values become `float`, and source timestamps become `datetime`. Models are frozen; source fields the package does not yet name remain available through each model's read-only `extra` mapping.

The client retries temporary transport failures, `429`, and `5xx` responses with bounded exponential backoff (default `RetryPolicy(max_attempts=3, initial_delay=0.25, max_delay=4.0)`), honoring `Retry-After` up to the configured maximum delay. Tune it per client:

```python
from py_understat import RetryPolicy, UnderstatClient

async with UnderstatClient(
    timeout=10.0,
    retry_policy=RetryPolicy(max_attempts=5, initial_delay=0.5, max_delay=8.0),
) as client:
    ...
```

Catch package-level errors rather than HTTPX implementation errors:

```python
from py_understat import RateLimitError, ResourceNotFoundError, UnderstatError

try:
    async with UnderstatClient() as client:
        snapshot = await client.player(8260).get()
except ResourceNotFoundError:
    print("Unknown Understat player")
except RateLimitError:
    print("Understat still rate-limited the request after retries")
except UnderstatError as error:
    print(f"Understat is unavailable: {error}")
```

The client sends an identifying user agent. It intentionally has no automatic cache or global rate limiter; callers needing either should apply them around immutable snapshots.

## Development

```bash
uv sync --all-groups   # install package + development tools
uv run ruff format .   # formatting
uv run ruff check .    # linting
uv run ty check        # type checking
uv run pytest          # tests
```

CI runs all four checks on every push and pull request (`.github/workflows/ci.yml`), and again as a gate before every release.

## Collaboration

See [collaboration.md](collaboration.md) for branch protection, pull request, development, and release guidance.

## Releases

Releases are fully automated from a version tag:

1. Bump the version in `pyproject.toml` (and `__version__` in `src/py_understat/__init__.py`).
2. Push a matching tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.

The [`publish` workflow](.github/workflows/publish.yml) then:

1. Runs formatting, lint, type checks, and tests.
2. Builds the sdist and wheel.
3. Publishes both to PyPI via trusted publishing (no stored credentials).
4. Creates a GitHub Release for the tag with the built distributions attached and auto-generated release notes.

## License

[MIT](LICENSE). Understat data remains the property of its respective owners; this client is provided as-is without affiliation or warranty.
