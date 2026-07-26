from datetime import date

from .model import ConsistencyViolation, Severity, WorldState


class TimelineAuditor:
    """Read-only audit of facts already committed to a timeline."""

    def audit(self, state: WorldState) -> list[dict[str, object]]:
        findings: list[dict[str, object]] = []
        for match in state.matches:
            played = date.fromisoformat(str(match["date"]))
            for team_id in (str(match["home"]), str(match["away"])):
                team = state.teams.get(team_id)
                association = state.associations.get(team.association_id) if team else None
                entity = state.entities.get(association.entity_id) if association else None
                if not entity or not association or not entity.exists_on(played) or not association.active_on(played):
                    finding = ConsistencyViolation("AUDIT_INACTIVE_TEAM", played, "TIMELINE", [team_id], ["active participant"], "match involving inactive entity", "results and ratings require recalculation", ["restore pre-competition snapshot"], Severity.FATAL)
                    findings.append(finding.record)
        for edition in state.editions.values():
            unsupported = [team for team in edition.finalists if team not in edition.qualifiers and not edition.applications.get(team, "").startswith("AUTO_")]
            if unsupported:
                finding = ConsistencyViolation("AUDIT_MISSING_PATH", edition.starts, "QUALIFICATION", unsupported, ["qualification path"], "finalist has no basis", "edition requires recalculation", ["restore pre-qualification snapshot"])
                findings.append(finding.record)
        return findings

