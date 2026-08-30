"""Immutable models for data published by Understat."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceModel(BaseModel):
    """Base model retaining fields added by Understat after this release."""

    model_config = ConfigDict(extra="allow", frozen=True, populate_by_name=True)

    @property
    def extra(self) -> Mapping[str, Any]:
        """Source fields not represented by a named model attribute."""
        return MappingProxyType(self.model_extra or {})


class TeamReference(SourceModel):
    """A team referenced from a match."""

    id: int
    title: str
    short_title: str | None = None


class Score(SourceModel):
    """A value split by home and away team.

    ``None`` entries mark an unplayed fixture (new-season snapshots contain
    scheduled matches without results).
    """

    home: int | None = Field(alias="h")
    away: int | None = Field(alias="a")


class ExpectedGoals(SourceModel):
    """Expected goals split by home and away team.

    ``None`` entries mark an unplayed fixture without xG data.
    """

    home: float | None = Field(alias="h")
    away: float | None = Field(alias="a")


class Forecast(SourceModel):
    """Pre-match home win, draw, and away win probabilities."""

    home_win: float = Field(alias="w")
    draw: float = Field(alias="d")
    away_win: float = Field(alias="l")


class MatchRecord(SourceModel):
    """A match listed in a League or Team snapshot."""

    id: int
    is_result: bool = Field(alias="isResult")
    home: TeamReference = Field(alias="h")
    away: TeamReference = Field(alias="a")
    goals: Score
    expected_goals: ExpectedGoals = Field(alias="xG")
    played_at: datetime = Field(alias="datetime")
    forecast: Forecast | None = None
    side: str | None = None
    result: str | None = None


class PlayerStatistic(SourceModel):
    """A player's aggregate statistics for one source view."""

    position: str
    games: int
    goals: int
    shots: int
    minutes: int = Field(alias="time")
    expected_goals: float = Field(alias="xG")
    assists: int
    expected_assists: float = Field(alias="xA")
    key_passes: int
    non_penalty_goals: int = Field(alias="npg")
    non_penalty_expected_goals: float = Field(alias="npxG")
    expected_goals_chain: float = Field(alias="xGChain")
    expected_goals_buildup: float = Field(alias="xGBuildup")
    id: int | None = None
    player_name: str | None = None
    team_title: str | None = None
    season: int | None = None
    team: str | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None


class PlayerMatch(SourceModel):
    """A player's statistics from one match."""

    id: int
    season: int
    date: date
    position: str
    goals: int
    shots: int
    minutes: int = Field(alias="time")
    expected_goals: float = Field(alias="xG")
    assists: int
    expected_assists: float = Field(alias="xA")
    key_passes: int
    non_penalty_goals: int = Field(alias="npg")
    non_penalty_expected_goals: float = Field(alias="npxG")
    expected_goals_chain: float = Field(alias="xGChain")
    expected_goals_buildup: float = Field(alias="xGBuildup")
    home_team: str = Field(alias="h_team")
    away_team: str = Field(alias="a_team")


class TeamHistoryRecord(SourceModel):
    """One historical team performance used in a League snapshot."""

    date: datetime
    home_or_away: str = Field(alias="h_a")
    result: str
    scored: int
    missed: int
    expected_goals: float = Field(alias="xG")
    expected_goals_against: float = Field(alias="xGA")


class TeamSeason(SourceModel):
    """A team's season data inside a League snapshot."""

    id: int
    title: str
    history: tuple[TeamHistoryRecord, ...]


class AgainstStatistics(SourceModel):
    """The opponent side of one team statistic category."""

    shots: int
    goals: int
    expected_goals: float = Field(alias="xG")


class TeamStatistics(SourceModel):
    """One Team statistic category, such as ``OpenPlay``."""

    shots: int
    goals: int
    expected_goals: float = Field(alias="xG")
    against: AgainstStatistics


class PlayerProfile(SourceModel):
    """The identity information Understat publishes for a player."""

    id: int
    name: str
    favorite_position: str | None = None


class Shot(SourceModel):
    """One shot event."""

    id: int
    minute: int
    result: str
    x: float = Field(alias="X")
    y: float = Field(alias="Y")
    expected_goals: float = Field(alias="xG")
    player: str
    home_or_away: str = Field(alias="h_a")
    player_id: int
    situation: str
    season: int
    shot_type: str = Field(alias="shotType")
    match_id: int
    home_team: str = Field(alias="h_team")
    away_team: str = Field(alias="a_team")
    date: datetime


class RosterEntry(SourceModel):
    """A player's appearance record in a Match snapshot."""

    id: int
    player_id: int
    team_id: int
    player: str
    position: str
    minutes: int = Field(alias="time")
    goals: int
    expected_goals: float = Field(alias="xG")
    assists: int
    expected_assists: float = Field(alias="xA")


class LeagueSnapshot(SourceModel):
    """The complete League resource snapshot for one competition season."""

    teams: Mapping[int, TeamSeason]
    players: tuple[PlayerStatistic, ...]
    matches: tuple[MatchRecord, ...] = Field(alias="dates")


class TeamSnapshot(SourceModel):
    """The complete Team resource snapshot for one competition season."""

    players: tuple[PlayerStatistic, ...]
    matches: tuple[MatchRecord, ...] = Field(alias="dates")
    statistics: Mapping[str, Mapping[str, TeamStatistics]]


class PlayerSnapshot(SourceModel):
    """The complete Player resource snapshot."""

    player: PlayerProfile
    matches: tuple[PlayerMatch, ...]
    groups: Mapping[str, Any]
    shots: tuple[Shot, ...]
    positions: tuple[str, ...] = Field(default=(), alias="positionsList")


class MatchSnapshot(SourceModel):
    """The complete Match resource snapshot."""

    rosters: Mapping[str, Mapping[int, RosterEntry]]
    shots: Mapping[str, tuple[Shot, ...]]
    template: Mapping[str, Any] = Field(alias="tmpl")
