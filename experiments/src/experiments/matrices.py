from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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


def fixture_matrices(size: int) -> TravelMatrices:
    async def fetch(i: int, j: int) -> TravelLeg:
        if i == j:
            return TravelLeg(time=0.0, distance=0.0)
        scale = 1.0 + abs(i - j) * 0.08
        return TravelLeg(time=9.0 * scale, distance=650.0 * scale)

    legs = AsyncLazyMatrix(size, fetch)
    t = AsyncMatrixFieldView(legs, "time")
    d = AsyncMatrixFieldView(legs, "distance")
    return TravelMatrices(t, d, t, d, t, d)


@asynccontextmanager
async def load_matrices(
    *,
    scenario: Scenario,
    mode: str,
    database_url: str | None = None,
    graphhopper_base_url: str | None = None,
) -> AsyncIterator[TravelMatrices]:
    if mode == "fixture":
        yield fixture_matrices(scenario.n_attractions)
        return

    db_url = database_url or os.environ.get("DATABASE_URL")
    gh_url = graphhopper_base_url or os.environ.get("GRAPHHOPPER_BASE_URL")
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
