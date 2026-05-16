import asyncio
import os
from enum import Enum
from typing import Any, Callable, TypedDict

import httpx
from asyncpg import Pool
from pydantic import BaseModel

from core import Point
from core.exceptions import ConfigurationError, RouteNotFoundCode, RouteNotFoundError
from core.route_cache import RouteCache
from core.stops import get_nearest_stops_in_radius
from core.trips import StopsTrip, get_average_trips_between_stops_groups

GRAPHHOPPER_CONCURRENCY = 10


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


def _cache_key(profile: EProfile, from_point: Point, to_point: Point) -> tuple:
    return (
        profile.value,
        round(from_point.lat, 5),
        round(from_point.lon, 5),
        round(to_point.lat, 5),
        round(to_point.lon, 5),
    )


def _public_transport_cache_key(
    from_point: Point, to_point: Point, radius: float, max_count: int
) -> tuple:
    return (
        "public-transport",
        round(from_point.lat, 5),
        round(from_point.lon, 5),
        round(to_point.lat, 5),
        round(to_point.lon, 5),
        round(radius, 1),
        max_count,
    )


def best_path_by(
    data: dict[str, Any], criterion: Callable[[dict], float]
) -> Path:
    if not (paths := data.get("paths")) or not isinstance(paths, list):
        raise RoutingError("GraphHopper response is empty")

    best_path = None

    for path in paths:
        if not isinstance(path, dict):
            raise RoutingError("GraphHopper path entry is not an object")

        distance = path.get("distance")
        if not isinstance(distance, (int, float)):
            continue

        value = criterion(path)
        if best_path is None or value > criterion(best_path):
            best_path = path

    if best_path is None:
        raise RoutingError("No valid path in GraphHopper response")

    return best_path


def get_shortest_path(data: dict[str, Any]) -> Path:
    return best_path_by(data, lambda p: -float(p["distance"]))


def _path_to_route_summary(path: dict[str, Any]) -> RouteSummary:
    distance = path.get("distance")
    time_ms = path.get("time")

    if distance is None or time_ms is None:
        raise RoutingError("GraphHopper path is missing distance or time")

    if not isinstance(distance, (int, float)) or not isinstance(time_ms, (int, float)):
        raise RoutingError("GraphHopper path distance or time is not numeric")

    return RouteSummary(
        distance=float(distance),
        time=float(time_ms) / 1000,
    )


async def calculate_route_between(
    client: httpx.AsyncClient,
    from_point: Point,
    to_point: Point,
    profile: EProfile,
    cache: RouteCache[RouteSummary] | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> RouteSummary:
    key = _cache_key(profile, from_point, to_point)
    if cache is not None:
        cached = cache.get(key)
        if cached is not None:
            return cached

    async def _fetch() -> RouteSummary:
        if cache is not None:
            cached = cache.get(key)
            if cached is not None:
                return cached

        base_url = os.environ.get("GRAPHHOPPER_BASE_URL", "")
        if not base_url:
            raise RoutingError("GRAPHHOPPER_BASE_URL is not configured")

        url = f"{base_url}/route"
        params: list[tuple[str, str]] = [
            ("point", f"{from_point.lat},{from_point.lon}"),
            ("point", f"{to_point.lat},{to_point.lon}"),
            ("profile", profile.value),
        ]

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RoutingError("GraphHopper unreachable: request timed out") from exc
        except httpx.HTTPError as exc:
            raise RoutingError(f"GraphHopper unreachable: {exc}") from exc

        data = response.json()

        if not isinstance(data, dict):
            raise RoutingError("GraphHopper returned a non-object JSON body")

        if msg := data.get("message") and not data.get("paths"):
            raise RoutingError(str(msg))

        route = _path_to_route_summary(get_shortest_path(data))
        if cache is not None:
            cache.set(key, route)
        return route

    if semaphore is not None:
        async with semaphore:
            return await _fetch()
    return await _fetch()


def _should_prune_leg(leg: RouteSummary, direct: RouteSummary) -> bool:
    return leg.distance > direct.distance or leg.time > direct.time


async def _fetch_foot_legs(
    client: httpx.AsyncClient,
    from_point: Point,
    to_point: Point,
    stop_trips: list[StopsTrip],
    cache: RouteCache[RouteSummary],
) -> dict[tuple[str, str], tuple[RouteSummary, RouteSummary]]:
    unique_pairs: dict[tuple[str, str], StopsTrip] = {}
    access_stops: dict[str, Point] = {}
    egress_stops: dict[str, Point] = {}

    for trip in stop_trips:
        pair_key = (trip.from_stop.id, trip.to_stop.id)
        if pair_key not in unique_pairs:
            unique_pairs[pair_key] = trip
        access_stops.setdefault(trip.from_stop.id, trip.from_stop.point)
        egress_stops.setdefault(trip.to_stop.id, trip.to_stop.point)

    semaphore = asyncio.Semaphore(GRAPHHOPPER_CONCURRENCY)

    access_stop_ids = list(access_stops.keys())
    egress_stop_ids = list(egress_stops.keys())

    access_results = await asyncio.gather(
        *[
            calculate_route_between(
                client,
                from_point,
                access_stops[stop_id],
                EProfile.Foot,
                cache,
                semaphore,
            )
            for stop_id in access_stop_ids
        ]
    )
    egress_results = await asyncio.gather(
        *[
            calculate_route_between(
                client,
                egress_stops[stop_id],
                to_point,
                EProfile.Foot,
                cache,
                semaphore,
            )
            for stop_id in egress_stop_ids
        ]
    )

    access_by_stop = dict(zip(access_stop_ids, access_results))
    egress_by_stop = dict(zip(egress_stop_ids, egress_results))

    return {
        pair_key: (
            access_by_stop[trip.from_stop.id],
            egress_by_stop[trip.to_stop.id],
        )
        for pair_key, trip in unique_pairs.items()
    }


async def calculate_public_transport_route_between(
    db: Pool,
    client: httpx.AsyncClient,
    from_point: Point,
    to_point: Point,
    radius: float,
    max_count: int,
    cache: RouteCache[RouteSummary] | None = None,
) -> RouteSummary:
    if cache is None:
        raise ConfigurationError("Route cache is not configured")
    route_cache = cache

    pt_key = _public_transport_cache_key(from_point, to_point, radius, max_count)
    cached_route = route_cache.get(pt_key)
    if cached_route is not None:
        return cached_route

    from_stops = await get_nearest_stops_in_radius(
        db,
        from_point,
        radius,
        max_count,
    )
    if not from_stops:
        raise RouteNotFoundError(
            RouteNotFoundCode.NO_STOPS_NEAR_ORIGIN,
            "No public transport stops found near the origin within the search radius.",
        )

    to_stops = await get_nearest_stops_in_radius(
        db,
        to_point,
        radius,
        max_count,
    )
    if not to_stops:
        raise RouteNotFoundError(
            RouteNotFoundCode.NO_STOPS_NEAR_DESTINATION,
            "No public transport stops found near the destination within the search radius.",
        )

    stop_trips = await get_average_trips_between_stops_groups(db, from_stops, to_stops)
    if not stop_trips:
        raise RouteNotFoundError(
            RouteNotFoundCode.NO_TRANSIT_LEGS,
            "No direct transit connections found between nearby stops.",
        )

    direct_route = await calculate_route_between(
        client, from_point, to_point, EProfile.Foot, route_cache
    )

    foot_legs = await _fetch_foot_legs(
        client, from_point, to_point, stop_trips, route_cache
    )

    best_route: RouteSummary | None = None
    evaluated_pairs: set[tuple[str, str]] = set()
    pruned_pairs: set[tuple[str, str]] = set()

    for stop_trip in stop_trips:
        pair_key = (stop_trip.from_stop.id, stop_trip.to_stop.id)
        if pair_key in evaluated_pairs:
            continue
        evaluated_pairs.add(pair_key)

        legs = foot_legs.get(pair_key)
        if legs is None:
            continue

        access_leg, egress_leg = legs
        if _should_prune_leg(access_leg, direct_route) or _should_prune_leg(
            egress_leg, direct_route
        ):
            pruned_pairs.add(pair_key)
            continue

        distance = access_leg.distance + egress_leg.distance
        time = access_leg.time + stop_trip.average_travel_time + egress_leg.time
        route = RouteSummary(distance=distance, time=time)

        if best_route is None or route.time < best_route.time:
            best_route = route

    if best_route is None:
        if evaluated_pairs and pruned_pairs == evaluated_pairs:
            raise RouteNotFoundError(
                RouteNotFoundCode.ALL_CANDIDATES_PRUNED,
                "All public transport options were discarded because walking to or from stops "
                "exceeds the direct walking route.",
            )
        raise RouteNotFoundError(
            RouteNotFoundCode.NO_VIABLE_ROUTE,
            "No viable public transport route could be assembled.",
        )

    route_cache.set(pt_key, best_route)
    return best_route
