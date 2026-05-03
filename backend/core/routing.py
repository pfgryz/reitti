import os
from enum import Enum
from typing import Any, Callable, Optional, TypedDict

import httpx
from asyncpg import Pool
from pydantic import BaseModel

from core import Point
from core.stops import get_nearest_stops_in_radius
from core.trips import get_average_trips_between_stops_groups


class EProfile(Enum):
    Foot = "foot"


class RouteSummary(BaseModel):
    distance: float
    time: float


class RoutingError(Exception):
    """Raised when GraphHopper cannot return a route or the response is invalid."""


class Path(TypedDict):
    distance: float
    time: float


def best_path_by(
    data: dict[str, Any], criterion: Callable[dict, float]
) -> Optional[Path]:
    if not (paths := data.get("paths")) or not isinstance(paths, list):
        raise RoutingError("GraphHopper response is empty")

    best_path = None

    for path in paths:
        if not isinstance(path, dict):
            raise RoutingError("GraphHopper path entry is not an object")

        value = criterion(path)
        if best_path is None or value > criterion(best_path):
            best_path = path

    return best_path


def get_shortest_path(data: dict[str, Any]) -> Path:
    return best_path_by(data, lambda path: -path.get("distance"))


def get_fastest_path(data: dict[str, Any]) -> Path:
    return best_path_by(data, lambda path: -path.get("time"))


async def calculate_route_between(
    client: httpx.AsyncClient,
    from_point: Point,
    to_point: Point,
    profile: EProfile,
) -> RouteSummary:
    url = f"{os.environ.get('GRAPHHOPPER_BASE_URL', '')}/route"

    params: list[tuple[str, str]] = [
        ("point", f"{from_point.lat},{from_point.lon}"),
        ("point", f"{to_point.lat},{to_point.lon}"),
        ("profile", profile.value),
    ]

    response = await client.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict):
        raise RoutingError("GraphHopper returned a non-object JSON body")

    if msg := data.get("message") and not data.get("paths"):
        raise RoutingError(str(msg))

    path = (
        get_shortest_path(data) if profile == EProfile.Foot else get_fastest_path(data)
    )

    return RouteSummary(distance=path.get("distance"), time=path.get("time") / 1000)


async def calculate_public_transport_route_between(
    db: Pool,
    client: httpx.AsyncClient,
    from_point: Point,
    to_point: Point,
    radius: float,
    max_count: int,
) -> RouteSummary:
    from_stops = await get_nearest_stops_in_radius(
        db,
        from_point,
        radius,
        max_count,
    )
    to_stops = await get_nearest_stops_in_radius(
        db,
        to_point,
        radius,
        max_count,
    )

    stop_trips = await get_average_trips_between_stops_groups(db, from_stops, to_stops)

    best_route = None

    for stop_trip in stop_trips:
        from_point_to_enter_stop = await calculate_route_between(
            client, from_point, stop_trip.from_stop.point, EProfile.Foot
        )
        exit_stop_to_end_point = await calculate_route_between(
            client, stop_trip.to_stop.point, to_point, EProfile.Foot
        )

        distance = from_point_to_enter_stop.distance + exit_stop_to_end_point.distance
        time = (
            from_point_to_enter_stop.time
            + stop_trip.average_travel_time
            + exit_stop_to_end_point.time
        )

        route = RouteSummary(distance=distance, time=time)

        if best_route is None or route.time < best_route.time:
            best_route = route

    return best_route
