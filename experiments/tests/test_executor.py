from __future__ import annotations

import pytest

from experiments.executor import run_case
from experiments.matrices import FixtureMatrixConfig, fixture_matrices
from experiments.scenarios import build_scenarios, setup_from_dict, suite_from_dict
from experiments.types import ASTAR_INTERVALS


@pytest.mark.asyncio
async def test_run_case_returns_ok_row() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {"n_attractions": [6], "seed_count": 1, "profiles": ["relaxed"]},
        name="synthetic_main",
    )
    scenario = build_scenarios(setup=setup, suite=suite)[0]
    matrices = fixture_matrices(
        scenario.n_attractions, FixtureMatrixConfig(), seed=scenario.seed
    )
    row = await run_case(
        variant=ASTAR_INTERVALS,
        scenario=scenario,
        mode="fixture",
        timeout_seconds=10.0,
        matrices=matrices,
    )
    assert row.status == "ok"
    assert row.experiment == ASTAR_INTERVALS.name
    assert row.scenario_id == scenario.id
    assert row.mode == "fixture"
    assert row.data_source == "fixture_synthetic"
    assert row.error is None
    assert row.expanded_nodes is not None
    assert row.visits_count is not None
    assert row.objective_cost is not None
