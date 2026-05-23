from __future__ import annotations

import pytest

from experiments.matrices import FixtureMatrixConfig, fixture_matrices
from experiments.scenarios import build_scenarios, setup_from_dict, suite_from_dict
from experiments.solver import run_variant
from experiments.types import ASTAR_INTERVALS, BF_INTERVALS


@pytest.mark.asyncio
async def test_solver_adapter_runs_astar_and_bruteforce() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {"n_attractions": [6], "seed_count": 1, "profiles": ["relaxed"]},
        name="synthetic_main",
    )
    scenario = build_scenarios(setup=setup, suite=suite)[0]
    matrices = fixture_matrices(
        scenario.n_attractions, FixtureMatrixConfig(), seed=scenario.seed
    )

    astar_result, astar_stats, _ = await run_variant(
        variant=ASTAR_INTERVALS,
        scenario=scenario,
        matrices=matrices,
        timeout_seconds=10.0,
    )
    bf_result, bf_stats, _ = await run_variant(
        variant=BF_INTERVALS,
        scenario=scenario,
        matrices=matrices,
        timeout_seconds=10.0,
    )
    assert len(astar_result.visits) >= 1
    assert len(bf_result.visits) >= 1
    assert astar_stats.expanded_nodes > 0
    assert bf_stats.expanded_nodes > 0
