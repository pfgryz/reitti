from typing import Literal

import httpx

from core import Point
from core.route_cache import RouteCache
from core.route_optimizer import (
    Attraction,
    AttractionType,
    OpeningHours,
    RouteOptimizationInput,
    RouteOptimizationResult,
    StayBounds,
    StaySelectionMode,
    TravelMatrices,
    VisitDecision,
)
from core.routing import EProfile, RouteSummary, RoutingError, calculate_route_between
from pydantic import BaseModel


class OpeningHoursInput(BaseModel):
    open: float
    close: float


class StayBoundsInput(BaseModel):
    min: float
    max: float


class AttractionInput(BaseModel):
    lat: float
    lon: float
    opening_hours: OpeningHoursInput
    stay: StayBoundsInput
    type: AttractionType = AttractionType.OTHER


class TripOptimizeRequest(BaseModel):
    start_time: float
    end_time: float | None = None
    attractions: list[AttractionInput]
    stay_mode: StaySelectionMode = StaySelectionMode.INTERVALS_15_MIN
    include_legs: bool = False

    def to_problem(self) -> RouteOptimizationInput:
        attrs = [
            Attraction(
                Point(lat=a.lat, lon=a.lon),
                OpeningHours(a.opening_hours.open, a.opening_hours.close),
                StayBounds(a.stay.min, a.stay.max),
                a.type,
            )
            for a in self.attractions
        ]
        return RouteOptimizationInput(
            self.start_time, attrs, self.end_time, self.stay_mode
        )


class VisitOutput(BaseModel):
    attraction_index: int
    arrival_time: float
    departure_time: float
    stay_minutes: float


class FootLegOutput(BaseModel):
    mode: Literal["foot"] = "foot"
    from_index: int
    to_index: int
    travel_time: float
    walk_distance: float
    points: list[tuple[float, float]]


class TripOptimizeResponse(BaseModel):
    visits: list[VisitOutput]
    end_time: float
    travel_time: float
    walk_distance: float
    legs: list[FootLegOutput] | None = None


async def _build_foot_legs(
    attractions: list[Attraction],
    visits: tuple[VisitDecision, ...],
    matrices: TravelMatrices,
    client: httpx.AsyncClient,
    route_cache: RouteCache[RouteSummary],
) -> list[FootLegOutput]:
    legs: list[FootLegOutput] = []
    prev = 0
    for visit in visits:
        to_idx = visit.attraction_index
        route = await calculate_route_between(
            client,
            attractions[prev].position,
            attractions[to_idx].position,
            EProfile.Foot,
            route_cache,
            include_geometry=True,
        )
        if not route.points:
            raise RoutingError("Foot route leg is missing geometry")
        legs.append(
            FootLegOutput(
                from_index=prev,
                to_index=to_idx,
                travel_time=await matrices.travel_time.get(prev, to_idx),
                walk_distance=await matrices.walk_dist.get(prev, to_idx),
                points=route.points,
            )
        )
        prev = to_idx
    return legs


async def from_result(
    result: RouteOptimizationResult,
    matrices: TravelMatrices,
    attractions: list[Attraction],
    *,
    include_legs: bool = False,
    client: httpx.AsyncClient | None = None,
    route_cache: RouteCache[RouteSummary] | None = None,
) -> TripOptimizeResponse:
    visits = [
        VisitOutput(
            attraction_index=v.attraction_index,
            arrival_time=v.arrival_time,
            departure_time=v.departure_time,
            stay_minutes=v.stay,
        )
        for v in result.visits
    ]
    travel_time = 0.0
    walk_distance = 0.0
    prev = 0
    for v in result.visits:
        travel_time += await matrices.travel_time.get(prev, v.attraction_index)
        walk_distance += await matrices.walk_dist.get(prev, v.attraction_index)
        prev = v.attraction_index

    legs = None
    if include_legs:
        if client is None or route_cache is None:
            raise ValueError("client and route_cache are required when include_legs is true")
        legs = await _build_foot_legs(
            attractions, result.visits, matrices, client, route_cache
        )

    return TripOptimizeResponse(
        visits=visits,
        end_time=result.end_time,
        travel_time=travel_time,
        walk_distance=walk_distance,
        legs=legs,
    )
