from __future__ import annotations

import asyncio

import pytest

from experiments.rows import data_source, row_ok, status_from_error
from experiments.scenarios import build_scenarios, setup_from_dict, suite_from_dict
from experiments.types import ASTAR_INTERVALS


def test_status_from_error_maps_expected_values() -> None:
    assert (
        status_from_error(Exception("Attraction 1 is individually infeasible."))
        == "infeasible"
    )
    assert status_from_error(Exception("No route found")) == "infeasible"
    assert status_from_error(Exception("timed out after 1.0s")) == "timeout"
    assert status_from_error(Exception("boom")) == "failed"


def test_status_from_error_maps_timeout_exception_types() -> None:
    assert status_from_error(TimeoutError()) == "timeout"
    assert status_from_error(asyncio.TimeoutError()) == "timeout"


def test_data_source_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="Unknown mode"):
        data_source("unsupported")


def test_row_ok_builds_successful_row() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {"n_attractions": [6], "seed_count": 1, "profiles": ["relaxed"]},
        name="synthetic_main",
    )
    scenario = build_scenarios(setup=setup, suite=suite)[0]

    row = row_ok(
        variant=ASTAR_INTERVALS,
        scenario=scenario,
        mode="fixture",
        wall_time_ms=123.0,
        peak_memory_mb=456.0,
        expanded_nodes=10,
        generated_nodes=11,
        pruned_by_best_g=12,
        visits_count=5,
        total_stay_minutes=78.0,
        stay_utilization=0.65,
        total_walk_distance_m=987.0,
        objective_cost=321.0,
        end_time=1110.0,
    )

    assert row.experiment == ASTAR_INTERVALS.name
    assert row.scenario_id == scenario.id
    assert row.profile == scenario.profile
    assert row.suite == scenario.suite
    assert row.setup_name == scenario.setup_name
    assert row.stay_mode == ASTAR_INTERVALS.stay_mode.value
    assert row.mode == "fixture"
    assert row.data_source == "fixture_synthetic"
    assert row.status == "ok"
    assert row.n_attractions == scenario.n_attractions
    assert row.wall_time_ms == 123.0
    assert row.peak_memory_mb == 456.0
    assert row.expanded_nodes == 10
    assert row.generated_nodes == 11
    assert row.pruned_by_best_g == 12
    assert row.visits_count == 5
    assert row.total_stay_minutes == 78.0
    assert row.stay_utilization == 0.65
    assert row.total_walk_distance_m == 987.0
    assert row.objective_cost == 321.0
    assert row.bf_objective is None
    assert row.optimality_gap is None
    assert row.heuristic_speedup is None
    assert row.feasibility_correctness is None
    assert row.end_time == 1110.0
    assert row.seed == scenario.seed
    assert row.error is None
    assert row.timestamp_utc
