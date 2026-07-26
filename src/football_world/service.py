from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any

from .audit import TimelineAuditor
from .engine import WorldEngine, build_playable_world
from .model import WorldState
from .persistence import dumps_world, loads_world
from .store import WorldStore


class WorldService:
    CURRENT = "current"
    SAVE = "manual-save"

    def __init__(self, store: WorldStore) -> None:
        self.store = store

    def _load(self) -> WorldState:
        payload = self.store.get(self.CURRENT)
        if payload is None:
            world = build_playable_world()
            self._persist(world)
            return world
        return loads_world(payload)

    def _persist(self, world: WorldState) -> None:
        self.store.put(self.CURRENT, dumps_world(world))

    def new_world(self, seed: int, scenario: str = "EGYPT_1934") -> dict[str, Any]:
        if scenario != "EGYPT_1934":
            raise ValueError("지원되는 MVP 시나리오는 EGYPT_1934뿐입니다.")
        world = build_playable_world(seed, egypt_wins=True)
        self._persist(world)
        return self.summary(world)

    def advance(self, mode: str, amount: int) -> dict[str, Any]:
        if mode not in {"DAY", "WEEK", "MONTH", "YEAR", "NEXT_EVENT"} or not 1 <= amount <= 100:
            raise ValueError("mode 또는 amount가 올바르지 않습니다.")
        world = self._load()
        engine = WorldEngine(world)
        if mode == "NEXT_EVENT":
            target = world.events[0].when if world.events else world.current_date
        elif mode == "DAY":
            target = world.current_date + timedelta(days=amount)
        elif mode == "WEEK":
            target = world.current_date + timedelta(weeks=amount)
        elif mode == "YEAR":
            target = _add_months(world.current_date, amount * 12)
        else:
            target = _add_months(world.current_date, amount)
        engine.advance_to(target)
        self._persist(world)
        return self.summary(world)

    def save(self) -> dict[str, Any]:
        world = self._load()
        self.store.put(self.SAVE, dumps_world(world))
        return {"savedAtWorldDate": world.current_date.isoformat(), "slot": self.SAVE}

    def saved(self) -> dict[str, Any] | None:
        payload = self.store.get(self.SAVE)
        return None if payload is None else self.summary(loads_world(payload))

    def load_save(self) -> dict[str, Any]:
        payload = self.store.get(self.SAVE)
        if payload is None:
            raise ValueError("불러올 저장 데이터가 없습니다.")
        world = loads_world(payload)
        self._persist(world)
        return self.summary(world)

    def summary(self, world: WorldState | None = None) -> dict[str, Any]:
        world = world or self._load()
        active = [edition for edition in world.editions.values() if not edition.completed and edition.starts.year >= world.current_date.year - 1]
        return {
            "date": world.current_date.isoformat(), "seed": world.seed,
            "scenario": "EGYPT_1934", "saveVersion": world.save_version,
            "storage": self.store.description,
            "warning": "개발용 수직 슬라이스: 실제 역사 전체 데이터가 아직 포함되지 않았습니다.",
            "teamCount": len(world.teams), "competitionCount": len(world.editions),
            "matchCount": len(world.matches), "auditErrorCount": len(TimelineAuditor().audit(world)),
            "activeCompetitions": [edition.id for edition in active],
            "nextEvent": _event(world.events[0]) if world.events else None,
            "recentMatches": list(reversed(world.matches[-5:])),
        }

    def teams(self) -> list[dict[str, Any]]:
        world = self._load()
        return [{"id": team.id, "name": world.entities[world.associations[team.association_id].entity_id].display_name, "rating": team.rating, "reputation": team.reputation, "experience": team.experience, "confederation": world.associations[team.association_id].confederation} for team in world.teams.values()]

    def team(self, team_id: str) -> dict[str, Any]:
        rows = {row["id"]: row for row in self.teams()}
        if team_id not in rows: raise KeyError(team_id)
        world = self._load(); team = world.teams[team_id]
        return {**rows[team_id], "attack": team.attack, "defence": team.defence, "goalkeeping": team.goalkeeping, "organisation": team.organisation, "footballCulture": team.football_culture, "infrastructure": team.infrastructure, "matches": [m for m in world.matches if team_id in (m["home"], m["away"])]}

    def competitions(self) -> list[dict[str, Any]]:
        world = self._load()
        return [_edition(item) for item in world.editions.values()]

    def competition(self, edition_id: str) -> dict[str, Any]:
        world = self._load()
        if edition_id not in world.editions: raise KeyError(edition_id)
        edition = world.editions[edition_id]
        return {**_edition(edition), "applications": edition.applications, "qualifiers": edition.qualifiers, "finalists": edition.finalists, "matches": [m for m in world.matches if m["edition_id"] == edition_id], "rules": edition.rules}

    def matches(self) -> list[dict[str, Any]]: return self._load().matches
    def timeline(self) -> list[dict[str, Any]]:
        world = self._load()
        history = [{"date": row.when.isoformat(), "kind": row.kind, "entities": row.entities, "reason": row.reason_code, "basis": row.basis} for row in world.audit_log]
        future = [{**_event(row), "future": True} for row in sorted(world.events)]
        return sorted(history + future, key=lambda row: row["date"])
    def audit(self) -> list[dict[str, Any]]: return TimelineAuditor().audit(self._load())


def _event(event: Any) -> dict[str, Any]:
    return {"date": event.when.isoformat(), "kind": event.kind, "payload": event.payload}


def _edition(item: Any) -> dict[str, Any]:
    return {"id": item.id, "competitionId": item.competition_id, "year": item.year, "starts": item.starts.isoformat(), "completed": item.completed, "championId": item.champion_id, "finalists": item.finalists}


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year, month = value.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))
