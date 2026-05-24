from typing import Literal

from core.route_optimizer import AttractionType, StaySelectionMode
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


class VisitOutput(BaseModel):
    attraction_index: int
    arrival_time: float
    departure_time: float
    stay_minutes: float


class LatLon(BaseModel):
    lat: float
    lon: float


class FootLegOutput(BaseModel):
    mode: Literal["foot"] = "foot"
    from_index: int
    to_index: int
    travel_time: float
    walk_distance: float
    points: list[tuple[float, float]]


class PublicTransportLegOutput(BaseModel):
    mode: Literal["public_transport"] = "public_transport"
    from_index: int
    to_index: int
    travel_time: float
    walk_distance: float
    from_stop: LatLon
    to_stop: LatLon
    access_points: list[tuple[float, float]]
    egress_points: list[tuple[float, float]]


TripLegOutput = FootLegOutput | PublicTransportLegOutput


class TripOptimizeResponse(BaseModel):
    visits: list[VisitOutput]
    end_time: float
    travel_time: float
    walk_distance: float
    legs: list[TripLegOutput] | None = None
