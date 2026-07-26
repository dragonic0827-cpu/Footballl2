from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class Severity(str, Enum):
    FATAL = "FATAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    WARNING = "WARNING"


class ConsistencyViolation(RuntimeError):
    """A structured, blocking precondition failure; never a narrative repair."""

    def __init__(
        self,
        violation_id: str,
        detected_at: date,
        category: str,
        affected_entities: list[str],
        violated_rules: list[str],
        factual_basis: str,
        simulation_impact: str,
        repair_options: list[str],
        severity: Severity = Severity.FATAL,
    ) -> None:
        self.record = {
            "violationId": violation_id,
            "detectedAt": detected_at.isoformat(),
            "severity": severity.value,
            "category": category,
            "affectedEntities": affected_entities,
            "conflictingEvents": [],
            "violatedRules": violated_rules,
            "factualBasis": factual_basis,
            "simulationImpact": simulation_impact,
            "repairOptions": repair_options,
            "automaticRepairAllowed": False,
        }
        super().__init__(f"정합성 오류: {category}: {factual_basis}")


@dataclass
class PoliticalEntity:
    id: str
    display_name: str
    existed_from: date
    existed_until: date | None = None
    predecessors: list[str] = field(default_factory=list)
    successors: list[str] = field(default_factory=list)

    def exists_on(self, on: date) -> bool:
        return self.existed_from <= on and (self.existed_until is None or on <= self.existed_until)


@dataclass
class Association:
    id: str
    entity_id: str
    founded: date
    active_until: date | None = None
    fifa_from: date | None = None
    confederation: str | None = None

    def active_on(self, on: date) -> bool:
        return self.founded <= on and (self.active_until is None or on <= self.active_until)


@dataclass
class NationalTeam:
    id: str
    association_id: str
    attack: float = 50
    defence: float = 50
    goalkeeping: float = 50
    organisation: float = 50
    experience: float = 10
    reputation: float = 10
    football_culture: float = 10
    infrastructure: float = 10
    rating: float = 1500


@dataclass
class RuleMetadata:
    id: str
    name: str
    authority: str
    effective_from: date
    source: str
    status: str


@dataclass
class CompetitionEdition:
    id: str
    competition_id: str
    year: int
    starts: date
    finals_slots: int
    rules_frozen_at: date
    rules: dict[str, Any]
    rule_metadata: list[RuleMetadata]
    applications: dict[str, str] = field(default_factory=dict)
    qualifiers: dict[str, str] = field(default_factory=dict)
    finalists: list[str] = field(default_factory=list)
    champion_id: str | None = None
    completed: bool = False


@dataclass(order=True)
class ScheduledEvent:
    when: date
    priority: int
    sequence: int
    kind: str = field(compare=False)
    payload: dict[str, Any] = field(default_factory=dict, compare=False)


@dataclass
class AuditEntry:
    when: date
    kind: str
    entities: list[str]
    reason_code: str
    basis: str


@dataclass
class WorldState:
    current_date: date
    seed: int
    save_version: int = 1
    rng_counter: int = 0
    event_sequence: int = 0
    entities: dict[str, PoliticalEntity] = field(default_factory=dict)
    associations: dict[str, Association] = field(default_factory=dict)
    teams: dict[str, NationalTeam] = field(default_factory=dict)
    editions: dict[str, CompetitionEdition] = field(default_factory=dict)
    events: list[ScheduledEvent] = field(default_factory=list)
    matches: list[dict[str, Any]] = field(default_factory=list)
    audit_log: list[AuditEntry] = field(default_factory=list)
    deferred_effects: list[dict[str, Any]] = field(default_factory=list)

    def canonical_dict(self) -> dict[str, Any]:
        return asdict(self)

