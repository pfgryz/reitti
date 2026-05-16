import math

from core import Point

EARTH_RADIUS_M = 6_371_000


def haversine_distance_m(from_point: Point, to_point: Point) -> float:
    lat1 = math.radians(from_point.lat)
    lat2 = math.radians(to_point.lat)
    d_lat = math.radians(to_point.lat - from_point.lat)
    d_lon = math.radians(to_point.lon - from_point.lon)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
