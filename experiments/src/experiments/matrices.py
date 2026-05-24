from __future__ import annotations

import os
import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import asyncpg
import httpx

from . import ensure_backend_path

if TYPE_CHECKING:
    from .scenarios import Scenario

ensure_backend_path()

from core.lazy_matrix import AsyncLazyMatrix, AsyncMatrixFieldView  # noqa: E402
from core.route_cache import RouteCache  # noqa: E402
from core.route_optimizer import (  # noqa: E402
    TravelLeg,
    TravelMatrices,
    create_travel_matrices,
)
from core.routing import RouteSummary  # noqa: E402


@dataclass(frozen=True, slots=True)
class FixtureMatrixConfig:
    density: float = 1.0
    disconnected_prob: float = 0.0
    time_min: float = 5.0
    time_max: float = 45.0
    pt_faster_prob: float = 0.35
    pt_speedup_min: float = 1.05
    pt_speedup_max: float = 1.80


class MatrixProvider(Protocol):
    @asynccontextmanager
    async def acquire(self, scenario: "Scenario") -> AsyncIterator[TravelMatrices]:
        yield fixture_matrices(1, FixtureMatrixConfig())


def precompute_fixture_edges(
    size: int, config: FixtureMatrixConfig, *, seed: int = 0
) -> tuple[list[list[float | None]], list[list[float | None]]]:
    """Eagerly sample a symmetric travel matrix as a pure function of (size, config, seed).

    Returns (times, dists). Entries are None for disconnected pairs and 0.0 on the diagonal.
    The pt_faster speedup is baked in here so the runtime matrix has no lazy randomness.
    """
    rng = random.Random(seed)
    density = min(max(config.density, 0.0), 1.0)
    connected_prob = density * (1.0 - config.disconnected_prob)
    times: list[list[float | None]] = [
        [0.0 if i == j else None for j in range(size)] for i in range(size)
    ]
    dists: list[list[float | None]] = [
        [0.0 if i == j else None for j in range(size)] for i in range(size)
    ]
    for i in range(size):
        for j in range(i + 1, size):
            if rng.random() >= connected_prob:
                continue
            base_time = rng.uniform(config.time_min, config.time_max)
            base_dist = base_time * rng.uniform(90.0, 140.0)
            if rng.random() < config.pt_faster_prob:
                base_time /= rng.uniform(config.pt_speedup_min, config.pt_speedup_max)
            times[i][j] = base_time
            times[j][i] = base_time
            dists[i][j] = base_dist
            dists[j][i] = base_dist
    return times, dists


def fixture_matrices(
    size: int, config: FixtureMatrixConfig, *, seed: int = 0
) -> TravelMatrices:
    times, dists = precompute_fixture_edges(size, config, seed=seed)

    async def travel(i: int, j: int) -> TravelLeg:
        t = times[i][j]
        d = dists[i][j]
        if t is None or d is None:
            return TravelLeg(time=1e9, distance=1e9)
        return TravelLeg(time=t, distance=d)

    legs = AsyncLazyMatrix(size, travel)
    t_view = AsyncMatrixFieldView(legs, "time")
    d_view = AsyncMatrixFieldView(legs, "distance")
    return TravelMatrices(t_view, d_view, t_view, d_view, t_view, d_view)


@dataclass(frozen=True, slots=True)
class FixtureMatrixProvider:
    config: FixtureMatrixConfig

    @asynccontextmanager
    async def acquire(self, scenario: "Scenario") -> AsyncIterator[TravelMatrices]:
        yield fixture_matrices(
            scenario.n_attractions,
            self.config,
            seed=scenario.seed,
        )


@dataclass(frozen=True, slots=True)
class RealMatrixProvider:
    database_url: str | None = None
    graphhopper_base_url: str | None = None

    @asynccontextmanager
    async def acquire(self, scenario: "Scenario") -> AsyncIterator[TravelMatrices]:
        db_url = self.database_url or os.environ.get("DATABASE_URL")
        gh_url = self.graphhopper_base_url or os.environ.get("GRAPHHOPPER_BASE_URL")
        if not db_url or not gh_url:
            raise RuntimeError("real mode needs DATABASE_URL and GRAPHHOPPER_BASE_URL")

        os.environ["GRAPHHOPPER_BASE_URL"] = gh_url
        pool = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=5)
        client = httpx.AsyncClient(timeout=30.0)
        cache: RouteCache[RouteSummary] = RouteCache()
        try:
            yield create_travel_matrices(
                scenario.problem.attractions,
                client=client,
                db=pool,
                route_cache=cache,
            )
        finally:
            await client.aclose()
            await pool.close()
