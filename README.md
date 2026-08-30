# py-understat

An asynchronous, typed client for football statistics published by [Understat](https://understat.com/). This is an unofficial client and is not affiliated with Understat.

## Install

```bash
uv add py-understat
```

From a checkout, install the package and its development tools with:

```bash
uv sync --all-groups
```

## Query data

`UnderstatClient` owns its HTTP resources. Use it as an async context manager.

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

Each `get()` call returns the complete snapshot Understat supplies for that resource:

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

- `League` is an enum containing Understat's six supported competitions.
- Team queries take the exact Understat team handle, such as `"Manchester_United"`.
- Player and Match queries take a positive Understat integer ID.
- League and Team queries take a competition season written as `"YYYY/YYYY+1"`, for example `"2025/2026"`. `Season("2025/2026")` is available when a reusable value is useful.

Invalid identifiers fail locally with `InvalidIdentifierError` before making a request.

## Data and failures

Known fields are normalized to native Python values: IDs and counts become `int`, expected-goal values become `float`, and source timestamps become `datetime`. Models are frozen, and source fields that the package does not yet name are available through each model's read-only `extra` mapping.

The client retries temporary transport failures, `429`, and `5xx` responses with bounded exponential backoff. It honors `Retry-After` up to the configured maximum delay. Catch package-level errors rather than HTTPX implementation errors:

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
