from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .model import (Association, AuditEntry, CompetitionEdition, NationalTeam,
                    PoliticalEntity, RuleMetadata, ScheduledEvent, WorldState)


def save_world(state: WorldState, path: Path) -> None:
    path.write_text(json.dumps(asdict(state), ensure_ascii=False, sort_keys=True, default=str), encoding="utf-8")


def dumps_world(state: WorldState) -> str:
    """Serialize through the same versioned codec used by file saves."""
    return json.dumps(asdict(state), ensure_ascii=False, sort_keys=True, default=str)


def loads_world(payload: str) -> WorldState:
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        return load_world(Path(handle.name))


def load_world(path: Path) -> WorldState:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw["save_version"] != 1:
        raise ValueError(f"unsupported save version: {raw['save_version']}")
    state = WorldState(date.fromisoformat(raw["current_date"]), raw["seed"], raw["save_version"], raw["rng_counter"], raw["event_sequence"])
    state.entities = {key: PoliticalEntity(**{**value, "existed_from": date.fromisoformat(value["existed_from"]), "existed_until": date.fromisoformat(value["existed_until"]) if value["existed_until"] else None}) for key, value in raw["entities"].items()}
    state.associations = {key: Association(**{**value, "founded": date.fromisoformat(value["founded"]), "active_until": date.fromisoformat(value["active_until"]) if value["active_until"] else None, "fifa_from": date.fromisoformat(value["fifa_from"]) if value["fifa_from"] else None}) for key, value in raw["associations"].items()}
    state.teams = {key: NationalTeam(**value) for key, value in raw["teams"].items()}
    for key, value in raw["editions"].items():
        metadata = [RuleMetadata(**{**item, "effective_from": date.fromisoformat(item["effective_from"])}) for item in value.pop("rule_metadata")]
        state.editions[key] = CompetitionEdition(**{**value, "starts": date.fromisoformat(value["starts"]), "rules_frozen_at": date.fromisoformat(value["rules_frozen_at"]), "rule_metadata": metadata})
    state.events = [ScheduledEvent(date.fromisoformat(item["when"]), item["priority"], item["sequence"], item["kind"], item["payload"]) for item in raw["events"]]
    state.matches = raw["matches"]
    state.audit_log = [AuditEntry(**{**item, "when": date.fromisoformat(item["when"])}) for item in raw["audit_log"]]
    state.deferred_effects = raw["deferred_effects"]
    return state
