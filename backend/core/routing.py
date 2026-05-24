import asyncio
import os
from enum import Enum
from typing import Any, Callable, TypedDict

import httpx
from asyncpg import Pool
from pydantic import BaseModel

from core import Point
from core.exceptions import ConfigurationError, RouteNotFoundCode, RouteNotFoundError
from core.geo import haversine_distance_m
from core.route_cache import RouteCache
from core.stops import Stop, get_nearest_stops_in_radius
from core.trips import StopsTrip, get_average_trips_between_stops_groups

GRAPHHOPPER_CONCURRENCY = 10


class EProfile(Enum):
    Foot = "foot"


class RouteSummary(BaseModel):
    distance: float
    time: float
    walk_distance: float | None = None
    points: list[tuple[float, float]] | None = None
    access_points: list[tuple[float, float]] | None = None
    egress_points: list[tuple[float, float]] | None = None
    from_stop: Stop | None = None
    to_stop: Stop | None = None


class RoutingError(Exception):
    """Raised when GraphHopper cannot return a route or the response is invalid."""


class Path(TypedDict):
    distance: float
    time: float


def _cache_key(
    profile: EProfile,
    from_point: Point,
    to_point: Point,
    *,
    include_geometry: bool = False,
) -> tuple:
    return (
        profile.value,
        round(from_point.lat, 5),
        round(from_point.lon, 5),
        round(to_point.lat, 5),
        round(to_point.lon, 5),
        include_geometry,
    )


def _public_transport_cache_key(
    from_point: Point,
    to_point: Point,
    radius: float,
    max_count: int,
    *,
    include_geometry: bool = False,
) -> tuple:
    return (
        "public-transport",
        round(from_point.lat, 5),
        round(from_point.lon, 5),
        round(to_point.lat, 5),
        round(to_point.lon, 5),
        round(radius, 1),
        max_count,
        include_geometry,
    )


def best_path_by(data: dict[str, Any], criterion: Callable[[dict], float]) -> Path:
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


def _coordinates_to_lat_lon_pairs(
    coordinates: list[Any],
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for item in coordinates:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            raise RoutingError("GraphHopper path point is not a coordinate pair")

        lon, lat = float(item[0]), float(item[1])
        points.append((lat, lon))

    if not points:
        raise RoutingError("GraphHopper path points is empty")

    return points


def _parse_path_points(path: dict[str, Any]) -> list[tuple[float, float]]:
    raw = path.get("points")
    if raw is None:
        raise RoutingError("GraphHopper path is missing points")

    if isinstance(raw, str):
        raise RoutingError(
            "GraphHopper returned encoded polyline; use points_encoded=false"
        )

    if isinstance(raw, dict):
        if raw.get("type") != "LineString":
            raise RoutingError("GraphHopper path points has unsupported GeoJSON type")
        coordinates = raw.get("coordinates")
        if not isinstance(coordinates, list):
            raise RoutingError("GraphHopper LineString is missing coordinates")
        return _coordinates_to_lat_lon_pairs(coordinates)

    if isinstance(raw, list):
        return _coordinates_to_lat_lon_pairs(raw)

    raise RoutingError(
        f"GraphHopper path points has unsupported type: {type(raw).__name__}"
    )


def _path_to_route_summary(
    path: dict[str, Any], *, include_geometry: bool = False
) -> RouteSummary:
    distance = path.get("distance")
    time_ms = path.get("time")

    if distance is None or time_ms is None:
        raise RoutingError("GraphHopper path is missing distance or time")

    if not isinstance(distance, (int, float)) or not isinstance(time_ms, (int, float)):
        raise RoutingError("GraphHopper path distance or time is not numeric")

    points = _parse_path_points(path) if include_geometry else None

    return RouteSummary(
        distance=float(distance),
        time=float(time_ms) / 1000,
        points=points,
    )


def _points_close(
    a: tuple[float, float], b: tuple[float, float], *, eps: float = 1e-6
) -> bool:
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def stitch_point_sequences(
    segments: list[list[tuple[float, float]]],
) -> list[tuple[float, float]]:
    if not segments:
        return []

    stitched = list(segments[0])
    for segment in segments[1:]:
        if not segment:
            continue
        start = 1 if stitched and _points_close(stitched[-1], segment[0]) else 0
        stitched.extend(segment[start:])
    return stitched


async def calculate_route_between(
    client: httpx.AsyncClient,
    from_point: Point,
    to_point: Point,
    profile: EProfile,
    cache: RouteCache[RouteSummary] | None = None,
    semaphore: asyncio.Semaphore | None = None,
    *,
    include_geometry: bool = False,
) -> RouteSummary:
    key = _cache_key(profile, from_point, to_point, include_geometry=include_geometry)
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
        if include_geometry:
            params.extend(
                [
                    ("calc_points", "true"),
                    ("points_encoded", "false"),
                ]
            )

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

        route = _path_to_route_summary(
            get_shortest_path(data), include_geometry=include_geometry
        )
        if cache is not None:
            cache.set(key, route)
        return route

    if semaphore is not None:
        async with semaphore:
            return await _fetch()
    return await _fetch()


async def stitch_foot_route_geometry(
    client: httpx.AsyncClient,
    waypoints: list[Point],
    cache: RouteCache[RouteSummary] | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> list[tuple[float, float]]:
    if not waypoints:
        return []
    if len(waypoints) == 1:
        p = waypoints[0]
        return [(p.lat, p.lon)]

    segments: list[list[tuple[float, float]]] = []
    for i in range(len(waypoints) - 1):
        leg = await calculate_route_between(
            client,
            waypoints[i],
            waypoints[i + 1],
            EProfile.Foot,
            cache,
            semaphore,
            include_geometry=True,
        )
        if leg.points is None:
            raise RoutingError("Foot route leg is missing geometry")
        segments.append(leg.points)

    return stitch_point_sequences(segments)


def _should_prune_leg(leg: RouteSummary, direct: RouteSummary) -> bool:
    return leg.distance > direct.distance or leg.time > direct.time


def _filter_stops_by_direct_route(
    stops: list[Stop], anchor: Point, direct_route: RouteSummary
) -> list[Stop]:
    max_m = direct_route.distance
    return [stop for stop in stops if haversine_distance_m(anchor, stop.point) <= max_m]


async def _fetch_foot_legs(
    client: httpx.AsyncClient,
    from_point: Point,
    to_point: Point,
    stop_trips: list[StopsTrip],
    cache: RouteCache[RouteSummary],
    direct_route: RouteSummary,
    *,
    include_geometry: bool = False,
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

    max_m = direct_route.distance
    access_stops = {
        stop_id: point
        for stop_id, point in access_stops.items()
        if haversine_distance_m(from_point, point) <= max_m
    }
    egress_stops = {
        stop_id: point
        for stop_id, point in egress_stops.items()
        if haversine_distance_m(point, to_point) <= max_m
    }

    semaphore = asyncio.Semaphore(GRAPHHOPPER_CONCURRENCY)

    if not access_stops or not egress_stops:
        return {}

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
                include_geometry=include_geometry,
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
                include_geometry=include_geometry,
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


def _pt_leg_distance(
    access_leg: RouteSummary, trip: StopsTrip, egress_leg: RouteSummary
) -> float:
    transit_m = haversine_distance_m(trip.from_stop.point, trip.to_stop.point)
    return access_leg.distance + transit_m + egress_leg.distance


async def calculate_public_transport_route_between(
    db: Pool,
    client: httpx.AsyncClient,
    from_point: Point,
    to_point: Point,
    radius: float,
    max_count: int,
    cache: RouteCache[RouteSummary] | None = None,
    *,
    include_geometry: bool = False,
    direct_route: RouteSummary | None = None,
) -> RouteSummary:
    if cache is None:
        raise ConfigurationError("Route cache is not configured")
    route_cache = cache

    pt_key = _public_transport_cache_key(
        from_point, to_point, radius, max_count, include_geometry=include_geometry
    )
    cached_route = route_cache.get(pt_key)
    if cached_route is not None:
        return cached_route

    from_stops, to_stops = await asyncio.gather(
        get_nearest_stops_in_radius(db, from_point, radius, max_count),
        get_nearest_stops_in_radius(db, to_point, radius, max_count),
    )

    if direct_route is None:
        direct_route = await calculate_route_between(
            client, from_point, to_point, EProfile.Foot, route_cache
        )

    from_stops = _filter_stops_by_direct_route(from_stops, from_point, direct_route)
    to_stops = _filter_stops_by_direct_route(to_stops, to_point, direct_route)

    if not from_stops:
        raise RouteNotFoundError(
            RouteNotFoundCode.NO_STOPS_NEAR_ORIGIN,
            "No public transport stops found near the origin within the search radius.",
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

    foot_legs = await _fetch_foot_legs(
        client,
        from_point,
        to_point,
        stop_trips,
        route_cache,
        direct_route,
        include_geometry=include_geometry,
    )

    best_route: RouteSummary | None = None
    best_access: RouteSummary | None = None
    best_egress: RouteSummary | None = None
    best_trip: StopsTrip | None = None
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

        walk_m = access_leg.distance + egress_leg.distance
        distance = _pt_leg_distance(access_leg, stop_trip, egress_leg)
        time = access_leg.time + stop_trip.average_travel_time + egress_leg.time
        route = RouteSummary(distance=distance, time=time, walk_distance=walk_m)

        if best_route is None or route.time < best_route.time:
            best_route = route
            best_trip = stop_trip
            best_access = access_leg
            best_egress = egress_leg

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

    if include_geometry and best_trip and best_access and best_egress:
        best_route = best_route.model_copy(
            update={
                "access_points": best_access.points,
                "egress_points": best_egress.points,
                "from_stop": best_trip.from_stop,
                "to_stop": best_trip.to_stop,
            }
        )

    route_cache.set(pt_key, best_route)
    return best_route
