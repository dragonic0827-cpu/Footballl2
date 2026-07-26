from __future__ import annotations

import heapq
from datetime import date

from .model import (
    Association, AuditEntry, CompetitionEdition, ConsistencyViolation,
    NationalTeam, PoliticalEntity, RuleMetadata, ScheduledEvent, WorldState,
)
from .rng import DeterministicRng


class WorldEngine:
    """UI-independent engine that mutates the single authoritative world state."""

    def __init__(self, state: WorldState) -> None:
        self.state = state
        heapq.heapify(self.state.events)
        self.rng = DeterministicRng(state.seed, state.rng_counter)

    def schedule(self, when: date, priority: int, kind: str, **payload: object) -> None:
        self.state.event_sequence += 1
        heapq.heappush(self.state.events, ScheduledEvent(when, priority, self.state.event_sequence, kind, payload))

    def advance_to(self, target: date) -> None:
        if target < self.state.current_date:
            raise ValueError("world time cannot move backwards")
        while self.state.events and self.state.events[0].when <= target:
            event = heapq.heappop(self.state.events)
            self.state.current_date = event.when
            self._handle(event)
        self.state.current_date = target
        self.state.rng_counter = self.rng.counter

    def _handle(self, event: ScheduledEvent) -> None:
        if event.kind == "MATCH":
            self.play_match(**event.payload)
        elif event.kind == "APPLY_EFFECT":
            team = self.state.teams[str(event.payload["team_id"])]
            setattr(team, str(event.payload["field"]), getattr(team, str(event.payload["field"])) + float(event.payload["amount"]))
        else:
            raise ConsistencyViolation("UNKNOWN_EVENT", event.when, "EVENT", [], ["known event type"], event.kind, "timeline stopped", ["remove or implement event"])

    def validate_team(self, team_id: str, on: date) -> None:
        team = self.state.teams[team_id]
        association = self.state.associations[team.association_id]
        entity = self.state.entities[association.entity_id]
        if not entity.exists_on(on) or not association.active_on(on):
            raise ConsistencyViolation("INACTIVE_TEAM", on, "ELIGIBILITY", [team_id], ["entity and association active"], "participant is inactive", "match cannot be generated", ["cancel", "reschedule", "record succession"])

    def freeze_and_validate_edition(self, edition_id: str) -> None:
        edition = self.state.editions[edition_id]
        if edition.rules_frozen_at >= edition.starts or not edition.rule_metadata:
            raise ConsistencyViolation("RULES_NOT_FROZEN", self.state.current_date, "RULES", [edition_id], ["rules frozen before first match", "sourced rules"], "incomplete rules", "competition cannot start", ["supply authoritative rule data"])
        if edition.rules.get("format") == "KNOCKOUT" and "points" in edition.rules:
            raise ConsistencyViolation("UNUSED_POINTS", self.state.current_date, "RULES", [edition_id], ["format-appropriate rules"], "knockout rules contain points", "ambiguous standings", ["remove points rule"])

    def approve_entry(self, edition_id: str, team_id: str, reason: str) -> None:
        edition = self.state.editions[edition_id]
        self.validate_team(team_id, edition.starts)
        edition.applications[team_id] = reason
        self.state.audit_log.append(AuditEntry(self.state.current_date, "ENTRY_APPROVED", [edition_id, team_id], reason, "eligibility gate passed"))

    def finalize_participants(self, edition_id: str) -> None:
        edition = self.state.editions[edition_id]
        self.freeze_and_validate_edition(edition_id)
        entrants = set(edition.qualifiers)
        for team_id, basis in edition.applications.items():
            if basis.startswith("AUTO_"):
                entrants.add(team_id)
        if len(entrants) != edition.finals_slots:
            raise ConsistencyViolation("SLOT_MISMATCH", self.state.current_date, "QUALIFICATION", [edition_id], ["qualifying basis for every finalist"], f"expected {edition.finals_slots}, got {len(entrants)}", "draw blocked", ["complete qualifiers", "correct slot allocation"])
        edition.finalists = sorted(entrants)

    def play_match(self, home_id: str, away_id: str, edition_id: str, forced_winner: str | None = None) -> dict[str, object]:
        on = self.state.current_date
        if home_id == away_id:
            raise ConsistencyViolation("SAME_TEAM", on, "MATCH", [home_id], ["exactly two distinct teams"], "duplicate participant", "result blocked", ["correct fixture"])
        self.validate_team(home_id, on); self.validate_team(away_id, on)
        edition = self.state.editions[edition_id]
        self.freeze_and_validate_edition(edition_id)
        a, b = self.state.teams[home_id], self.state.teams[away_id]
        expectation = 1 / (1 + 10 ** ((b.rating - a.rating) / 400))
        winner = forced_winner or (home_id if self.rng.random(f"match:{edition_id}:{home_id}:{away_id}") < expectation else away_id)
        actual = 1.0 if winner == home_id else 0.0
        delta = 24 * (actual - expectation)
        a.rating += delta; b.rating -= delta
        result = {"date": on.isoformat(), "edition_id": edition_id, "home": home_id, "away": away_id, "winner": winner, "rating_delta": {home_id: delta, away_id: -delta}}
        self.state.matches.append(result)
        return result

    def crown_champion(self, edition_id: str, team_id: str) -> None:
        edition = self.state.editions[edition_id]
        if team_id not in edition.finalists:
            raise ConsistencyViolation("INELIGIBLE_CHAMPION", self.state.current_date, "COMPETITION", [edition_id, team_id], ["champion must be finalist"], "team lacks qualification path", "title blocked", ["recalculate competition"])
        edition.champion_id, edition.completed = team_id, True
        team = self.state.teams[team_id]
        # Reputation is immediate; culture and infrastructure mature later rather than
        # magically improving the current adult squad.
        team.reputation += 12 * (1 - team.reputation / 100)
        team.experience += 3 * (1 - team.experience / 100)
        for years, field, amount in ((3, "football_culture", 4.0), (7, "infrastructure", 2.0)):
            self.schedule(date(edition.year + years, 7, 1), 20, "APPLY_EFFECT", team_id=team_id, field=field, amount=amount)
        self.state.audit_log.append(AuditEntry(self.state.current_date, "CHAMPION", [edition_id, team_id], "FINAL_WINNER", "completed final"))

    def prepare_successor_edition(self, previous_id: str, next_id: str) -> None:
        previous, nxt = self.state.editions[previous_id], self.state.editions[next_id]
        if not previous.completed or previous.champion_id is None:
            raise ConsistencyViolation("NO_PREVIOUS_CHAMPION", self.state.current_date, "CONTINUITY", [previous_id], ["completed prior edition"], "champion unavailable", "successor preparation blocked", ["finish prior edition"])
        champion = previous.champion_id
        if nxt.rules.get("defending_champion_auto_qualifies"):
            self.approve_entry(next_id, champion, "AUTO_DEFENDING_CHAMPION")
        else:
            self.approve_entry(next_id, champion, "QUALIFYING_APPLICATION_DEFENDING_CHAMPION")


def build_early_world(seed: int = 1908) -> WorldState:
    state = WorldState(date(1908, 1, 1), seed)
    for entity_id, name, start in (("EGY", "이집트", date(1922, 2, 28)), ("ITA", "이탈리아", date(1861, 3, 17))):
        state.entities[entity_id] = PoliticalEntity(entity_id, name, start)
        association_id = f"FA-{entity_id}"
        founded = date(1921, 12, 3) if entity_id == "EGY" else date(1898, 3, 26)
        state.associations[association_id] = Association(association_id, entity_id, founded, fifa_from=founded, confederation="CAF" if entity_id == "EGY" else "UEFA")
        state.teams[entity_id] = NationalTeam(entity_id, association_id)
    source = RuleMetadata("WC-1934-BASE", "1934 World Championship test rules", "FIFA", date(1933, 1, 1), "project verified fixture", "USER_DEFINED")
    state.editions["WC1934"] = CompetitionEdition("WC1934", "WORLD_CUP", 1934, date(1934, 5, 27), 2, date(1934, 1, 1), {"format": "KNOCKOUT", "defending_champion_auto_qualifies": False}, [source], qualifiers={"EGY": "QUALIFIER", "ITA": "HOST_AUTO"})
    source38 = RuleMetadata("WC-1938-BASE", "1938 World Championship continuity rules", "FIFA", date(1937, 1, 1), "project verified fixture", "USER_DEFINED")
    state.editions["WC1938"] = CompetitionEdition("WC1938", "WORLD_CUP", 1938, date(1938, 6, 4), 2, date(1937, 12, 1), {"format": "KNOCKOUT", "defending_champion_auto_qualifies": True}, [source38], qualifiers={"ITA": "QUALIFIER"})
    return state
