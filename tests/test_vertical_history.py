from datetime import date

import pytest

from football_world.audit import TimelineAuditor
from football_world.engine import WorldEngine, build_early_world
from football_world.model import ConsistencyViolation
from football_world.persistence import load_world, save_world


def test_egypt_1934_champion_is_remembered_in_1938() -> None:
    state = build_early_world(42)
    engine = WorldEngine(state)
    engine.advance_to(date(1934, 5, 27))
    engine.finalize_participants("WC1934")
    engine.play_match("EGY", "ITA", "WC1934", forced_winner="EGY")
    before_culture = state.teams["EGY"].football_culture
    engine.crown_champion("WC1934", "EGY")
    engine.prepare_successor_edition("WC1934", "WC1938")
    engine.finalize_participants("WC1938")

    assert state.editions["WC1934"].champion_id == "EGY"
    assert state.teams["EGY"].reputation > 10
    assert state.teams["EGY"].football_culture == before_culture
    assert state.editions["WC1938"].applications["EGY"] == "AUTO_DEFENDING_CHAMPION"
    assert state.editions["WC1938"].finalists == ["EGY", "ITA"]


def test_inactive_entity_cannot_play_and_audit_detects_legacy_error() -> None:
    state = build_early_world()
    state.entities["EGY"].existed_until = date(1933, 1, 1)
    engine = WorldEngine(state)
    engine.advance_to(date(1934, 5, 27))
    with pytest.raises(ConsistencyViolation) as caught:
        engine.play_match("EGY", "ITA", "WC1934")
    assert caught.value.record["automaticRepairAllowed"] is False

    state.matches.append({"date": "1934-05-27", "home": "EGY", "away": "ITA"})
    assert TimelineAuditor().audit(state)[0]["severity"] == "FATAL"


def test_save_load_preserves_rng_and_future_result(tmp_path) -> None:
    uninterrupted = build_early_world(77)
    resumed = build_early_world(77)
    path = tmp_path / "world.json"
    save_world(resumed, path)
    resumed = load_world(path)

    results = []
    for state in (uninterrupted, resumed):
        engine = WorldEngine(state)
        engine.advance_to(date(1934, 5, 27))
        engine.finalize_participants("WC1934")
        results.append(engine.play_match("EGY", "ITA", "WC1934"))
    assert results[0] == results[1]
    assert uninterrupted.rng_counter == resumed.rng_counter


def test_finalists_require_a_qualification_or_auto_entry_basis() -> None:
    state = build_early_world()
    state.editions["WC1934"].qualifiers.clear()
    engine = WorldEngine(state)
    engine.advance_to(date(1934, 1, 1))
    with pytest.raises(ConsistencyViolation) as caught:
        engine.finalize_participants("WC1934")
    assert caught.value.record["category"] == "QUALIFICATION"

