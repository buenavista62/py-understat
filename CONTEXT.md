# Understat Data

This context retrieves football statistics published by Understat. It presents Understat resources through a stable Python API without redefining the source data.

## Language

**Understat resource**:
A top-level published data subject: a League, Team, Player, or Match.
_Avoid_: endpoint, entity

**Competition season**:
The campaign beginning in a given calendar year and ending in the next, represented publicly as `YYYY/YYYY+1`.
_Avoid_: year, calendar year

**Resource snapshot**:
The complete set of data Understat returns for one resource query.
_Avoid_: table, endpoint response

**Team handle**:
The exact URL-safe name Understat assigns to a Team, such as `Manchester_United`.
_Avoid_: team name, slug

**Understat ID**:
The positive integer that identifies a Player or Match in Understat data.
_Avoid_: identifier, string ID
