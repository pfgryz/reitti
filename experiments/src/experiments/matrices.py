from __future__ import annotations

import os
import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Protocol

import asyncpg
import httpx

from . import ensure_backend_path
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
    async def acquire(self, scenario: Scenario) -> AsyncIterator[TravelMatrices]:
        yield fixture_matrices(1, FixtureMatrixConfig())


def fixture_matrices(
    size: int, config: FixtureMatrixConfig, *, seed: int = 0
) -> TravelMatrices:
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
            times[i][j] = base_time
            times[j][i] = base_time
            dists[i][j] = base_dist
            dists[j][i] = base_dist

    async def travel(i: int, j: int) -> TravelLeg:
        if i == j:
            return TravelLeg(time=0.0, distance=0.0)
        time_value = times[i][j]
        dist_value = dists[i][j]
        if time_value is None or dist_value is None:
            # Keep an explicit large edge cost for disconnected pairs.
            return TravelLeg(time=1e9, distance=1e9)
        pt_faster = rng.random() < config.pt_faster_prob
        if pt_faster:
            speedup = rng.uniform(config.pt_speedup_min, config.pt_speedup_max)
            return TravelLeg(time=time_value / speedup, distance=dist_value)
        return TravelLeg(time=time_value, distance=dist_value)

    legs = AsyncLazyMatrix(size, travel)
    t = AsyncMatrixFieldView(legs, "time")
    d = AsyncMatrixFieldView(legs, "distance")
    return TravelMatrices(t, d, t, d, t, d)


@dataclass(frozen=True, slots=True)
class FixtureMatrixProvider:
    config: FixtureMatrixConfig

    @asynccontextmanager
    async def acquire(self, scenario: Scenario) -> AsyncIterator[TravelMatrices]:
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
    async def acquire(self, scenario: Scenario) -> AsyncIterator[TravelMatrices]:
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
