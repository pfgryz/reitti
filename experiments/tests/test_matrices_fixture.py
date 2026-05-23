from __future__ import annotations

import pytest

from experiments.matrices import (
    FixtureMatrixConfig,
    FixtureMatrixProvider,
    fixture_matrices,
)
from experiments.scenarios import build_scenarios, setup_from_dict, suite_from_dict


@pytest.mark.asyncio
async def test_fixture_provider_returns_finite_leg_times() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {"n_attractions": [6], "seed_count": 1, "profiles": ["relaxed"]},
        name="synthetic_main",
    )
    scenario = build_scenarios(setup=setup, suite=suite)[0]
    provider = FixtureMatrixProvider(FixtureMatrixConfig())
    async with provider.acquire(scenario) as matrices:
        t01 = await matrices.travel_time.get(0, 1)
        t10 = await matrices.travel_time.get(1, 0)
    assert t01 > 0.0
    assert t01 == pytest.approx(t10)


@pytest.mark.asyncio
async def test_fixture_density_zero_makes_off_diagonal_disconnected() -> None:
    dense = fixture_matrices(
        3, FixtureMatrixConfig(density=1.0, disconnected_prob=0.0), seed=7
    )
    sparse = fixture_matrices(
        3, FixtureMatrixConfig(density=0.0, disconnected_prob=0.0), seed=7
    )

    dense_t01 = await dense.travel_time.get(0, 1)
    sparse_t01 = await sparse.travel_time.get(0, 1)
    sparse_t10 = await sparse.travel_time.get(1, 0)

    assert dense_t01 < 1e9
    assert sparse_t01 == pytest.approx(1e9)
    assert sparse_t01 == pytest.approx(sparse_t10)


@pytest.mark.asyncio
async def test_fixture_matrices_are_deterministic_for_seed() -> None:
    cfg = FixtureMatrixConfig(density=0.55, disconnected_prob=0.2)
    m1 = fixture_matrices(4, cfg, seed=17)
    m2 = fixture_matrices(4, cfg, seed=17)

    for i in range(4):
        for j in range(4):
            t1 = await m1.travel_time.get(i, j)
            t2 = await m2.travel_time.get(i, j)
            assert t1 == pytest.approx(t2)
