from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from experiments.executor import run_case, run_suite
from experiments.matrices import (
    FixtureMatrixConfig,
    MatrixProvider,
    fixture_matrices,
)
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


class _ScenarioAwareProvider(MatrixProvider):
    @asynccontextmanager
    async def acquire(self, scenario) -> AsyncIterator:
        if scenario.seed % 2 == 0:
            raise RuntimeError("simulated provider failure")
        yield fixture_matrices(
            scenario.n_attractions, FixtureMatrixConfig(), seed=scenario.seed
        )


class _HangingProvider(MatrixProvider):
    def __init__(self, *, hung_seed: int) -> None:
        self._hung_seed = hung_seed

    @asynccontextmanager
    async def acquire(self, scenario) -> AsyncIterator:
        if scenario.seed == self._hung_seed:
            await asyncio.sleep(10.0)
        yield fixture_matrices(
            scenario.n_attractions, FixtureMatrixConfig(), seed=scenario.seed
        )


@pytest.mark.asyncio
async def test_run_suite_continues_after_provider_failure() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {"n_attractions": [6], "seed_count": 2, "profiles": ["relaxed"]},
        name="synthetic_main",
    )
    scenarios = build_scenarios(setup=setup, suite=suite)
    rows = await run_suite(
        scenarios=scenarios,
        variants=[ASTAR_INTERVALS],
        mode="fixture",
        timeout_seconds=3.0,
        suite_timeout_seconds=30.0,
        matrix_provider=_ScenarioAwareProvider(),
        desc="test",
    )
    assert len(rows) == 2
    assert {row.status for row in rows} == {"ok", "failed"}


@pytest.mark.asyncio
async def test_run_suite_hard_kills_hanging_case_and_continues() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {"n_attractions": [6], "seed_count": 2, "profiles": ["relaxed"]},
        name="synthetic_main",
    )
    scenarios = build_scenarios(setup=setup, suite=suite)
    provider = _HangingProvider(hung_seed=scenarios[0].seed)
    rows = await run_suite(
        scenarios=scenarios,
        variants=[ASTAR_INTERVALS],
        mode="fixture",
        timeout_seconds=0.5,
        suite_timeout_seconds=30.0,
        matrix_provider=provider,
        desc="test",
    )
    assert len(rows) == 2
    assert {row.status for row in rows} == {"ok", "timeout"}


@pytest.mark.asyncio
async def test_suite_timeout_is_soft_and_does_not_skip_tail() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {"n_attractions": [6], "seed_count": 3, "profiles": ["relaxed"]},
        name="synthetic_main",
    )
    scenarios = build_scenarios(setup=setup, suite=suite)
    provider = _HangingProvider(hung_seed=scenarios[0].seed)
    rows = await run_suite(
        scenarios=scenarios,
        variants=[ASTAR_INTERVALS],
        mode="fixture",
        timeout_seconds=0.5,
        suite_timeout_seconds=0.1,
        matrix_provider=provider,
        desc="test",
    )
    assert len(rows) == 3
    assert all(row.status != "skipped" for row in rows)
