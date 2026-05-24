from typing import Literal

from core import Point
from core.route_optimizer import (
    Attraction,
    AttractionType,
    OpeningHours,
    RouteOptimizationInput,
    RouteOptimizationResult,
    StayBounds,
    StaySelectionMode,
    TravelLeg,
    TravelMatrices,
)
from core.routing import RoutingError
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


class StopOutput(BaseModel):
    name: str
    lat: float
    lon: float


class LegOutput(BaseModel):
    mode: Literal["foot", "public_transport"]
    from_index: int
    to_index: int
    travel_time: float
    walk_distance: float
    distance: float
    points: list[tuple[float, float]] | None = None
    walk_to: list[tuple[float, float]] | None = None
    walk_from: list[tuple[float, float]] | None = None
    from_stop: StopOutput | None = None
    to_stop: StopOutput | None = None


class TripOptimizeResponse(BaseModel):
    visits: list[VisitOutput]
    end_time: float
    travel_time: float
    walk_distance: float
    distance: float
    legs: list[LegOutput] | None = None


def _leg_output(prev: int, to_idx: int, leg: TravelLeg) -> LegOutput:
    base = dict(
        mode=leg.mode,
        from_index=prev,
        to_index=to_idx,
        travel_time=leg.time,
        walk_distance=leg.walk_distance,
        distance=leg.distance,
    )
    if leg.mode == "foot":
        if not leg.points:
            raise RoutingError(f"Leg {prev}->{to_idx} is missing geometry")
        return LegOutput(**base, points=list(leg.points))
    if not leg.pt:
        raise RoutingError(f"Leg {prev}->{to_idx} is missing public transport details")
    p = leg.pt
    return LegOutput(
        **base,
        walk_to=list(p.walk_to),
        walk_from=list(p.walk_from),
        from_stop=StopOutput(name=p.from_stop.name, lat=p.from_stop.lat, lon=p.from_stop.lon),
        to_stop=StopOutput(name=p.to_stop.name, lat=p.to_stop.lat, lon=p.to_stop.lon),
    )


async def from_result(
    result: RouteOptimizationResult,
    matrices: TravelMatrices,
    *,
    include_legs: bool = False,
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
    distance = 0.0
    legs: list[LegOutput] | None = [] if include_legs else None
    prev = 0
    for v in result.visits:
        leg = await matrices.legs.get(prev, v.attraction_index)
        travel_time += leg.time
        walk_distance += leg.walk_distance
        distance += leg.distance
        if include_legs:
            legs.append(_leg_output(prev, v.attraction_index, leg))
        prev = v.attraction_index

    return TripOptimizeResponse(
        visits=visits,
        end_time=result.end_time,
        travel_time=travel_time,
        walk_distance=walk_distance,
        distance=distance,
        legs=legs,
    )
