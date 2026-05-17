from dataclasses import dataclass
from enum import Enum

import httpx
from asyncpg import Pool
from config import (
    MAX_PUBLIC_TRANSPORT_STOPS_TO_CONSIDER,
    MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT,
)

from core import Point
from core.exceptions import RouteNotFoundError
from core.lazy_matrix import AsyncLazyMatrix, AsyncMatrixFieldView
from core.route_cache import RouteCache
from core.routing import (
    EProfile,
    RouteSummary,
    calculate_public_transport_route_between,
    calculate_route_between,
)

# Cost weights (spec: β ≫ α — stay time dominates, then walking distance)
ALPHA = 1.0  # per meter walked
BETA = 10_000.0  # per minute of unused stay time

STAY_INTERVAL_MINUTES = 15


class AttractionType(str, Enum):
    MUSEUM = "museum"
    RESTAURANT = "restaurant"
    PARK = "park"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class OpeningHours:
    open: float
    close: float


@dataclass(frozen=True, slots=True)
class StayBounds:
    min: float
    max: float


@dataclass(frozen=True, slots=True)
class Attraction:
    position: Point
    opening_hours: OpeningHours
    stay: StayBounds
    type: AttractionType


@dataclass(frozen=True, slots=True)
class RouteOptimizationInput:
    start_time: float
    attractions: list[Attraction]
    end_time: float | None = None


@dataclass(frozen=True, slots=True)
class TravelLeg:
    time: float  # minutes
    distance: float  # meters


@dataclass(frozen=True, slots=True)
class TravelMatrices:
    foot_time: AsyncMatrixFieldView[TravelLeg, float]
    foot_distance: AsyncMatrixFieldView[TravelLeg, float]
    public_transport_time: AsyncMatrixFieldView[TravelLeg, float]
    public_transport_distance: AsyncMatrixFieldView[TravelLeg, float]
    travel_time: AsyncMatrixFieldView[TravelLeg, float]
    walk_dist: AsyncMatrixFieldView[TravelLeg, float]


def create_travel_matrices(
    attractions: list[Attraction],
    *,
    client: httpx.AsyncClient,
    db: Pool,
    route_cache: RouteCache[RouteSummary],
) -> TravelMatrices:
    n = len(attractions)
    points = [attraction.position for attraction in attractions]

    async def fetch_foot_leg(i: int, j: int) -> TravelLeg:
        if i == j:
            return TravelLeg(time=0.0, distance=0.0)
        route = await calculate_route_between(
            client, points[i], points[j], EProfile.Foot, route_cache
        )
        return TravelLeg(time=route.time / 60, distance=route.distance)

    async def fetch_public_transport_leg(i: int, j: int) -> TravelLeg:
        if i == j:
            return TravelLeg(time=0.0, distance=0.0)
        route = await calculate_public_transport_route_between(
            db,
            client,
            points[i],
            points[j],
            MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT,
            MAX_PUBLIC_TRANSPORT_STOPS_TO_CONSIDER,
            route_cache,
        )
        return TravelLeg(time=route.time / 60, distance=route.distance)

    foot_legs = AsyncLazyMatrix(n, fetch_foot_leg)
    public_transport_legs = AsyncLazyMatrix(n, fetch_public_transport_leg)

    async def fetch_optimal_leg(i: int, j: int) -> TravelLeg:
        if i == j:
            return TravelLeg(time=0.0, distance=0.0)
        foot = await foot_legs.get(i, j)
        try:
            pt = await public_transport_legs.get(i, j)
        except RouteNotFoundError:
            return foot
        return select_optimal_leg(foot, pt)

    optimal_legs = AsyncLazyMatrix(n, fetch_optimal_leg)
    return TravelMatrices(
        foot_time=AsyncMatrixFieldView(foot_legs, "time"),
        foot_distance=AsyncMatrixFieldView(foot_legs, "distance"),
        public_transport_time=AsyncMatrixFieldView(public_transport_legs, "time"),
        public_transport_distance=AsyncMatrixFieldView(
            public_transport_legs, "distance"
        ),
        travel_time=AsyncMatrixFieldView(optimal_legs, "time"),
        walk_dist=AsyncMatrixFieldView(optimal_legs, "distance"),
    )


def select_optimal_leg(foot: TravelLeg, pt: TravelLeg | None) -> TravelLeg:
    if pt is None:
        return foot
    if foot.time <= pt.time:
        return TravelLeg(time=foot.time, distance=foot.distance)
    return TravelLeg(time=pt.time, distance=pt.distance)


@dataclass(frozen=True, slots=True)
class SearchState:
    """s = (u, Visited, t) - current attraction, visited bitmask, departure time."""

    u: int
    visited: int
    t: float


async def optimize_route(problem: RouteOptimizationInput) -> None:
    travel_matrices = create_travel_matrices(
        problem.attractions,
        client=httpx.AsyncClient(),
        db=asyncpg.Pool(),
        route_cache=RouteCache[RouteSummary](),
    )

    raise NotImplementedError
