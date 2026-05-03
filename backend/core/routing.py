import os
from enum import Enum
from typing import Any, Callable, Optional, TypedDict

import httpx
from pydantic import BaseModel


class Point(BaseModel):
    lat: float
    lon: float


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


def best_path_by(data: dict[str, Any], f: Callable[str, float]) -> Optional[Path]:
    if not (paths := data.get("paths")) or not isinstance(paths, list):
        raise RoutingError("GraphHopper response is empty")

    best_path = None

    for path in paths:
        if not isinstance(path, dict):
            raise RoutingError("GraphHopper path entry is not an object")

        value = f(path)
        if best_path is None or value > f(best_path):
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
        ("point", f"{from_point.lon},{from_point.lat}"),
        ("point", f"{to_point.lon},{to_point.lat}"),
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
    print(path)
    return RouteSummary(distance=path.get("distance"), time=path.get("time") / 1000)
