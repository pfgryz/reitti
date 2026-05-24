import httpx
from asyncpg import Pool
from app.validators import LatQuery, LonQuery, RadiusQuery
from config import (
    MAX_PUBLIC_TRANSPORT_STOPS_TO_CONSIDER,
    MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT,
)
from core import Point
from core.dependencies import get_client, get_db, get_route_cache
from core.route_cache import RouteCache
from core.routing import (
    EProfile,
    RouteSummary,
    calculate_public_transport_route_between,
    calculate_route_between,
)
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/distance", tags=["distance"])


@router.get("/foot")
async def get_foot_route_request(
    from_lat: LatQuery,
    from_lon: LonQuery,
    to_lat: LatQuery,
    to_lon: LonQuery,
    geometry: bool = False,
    client: httpx.AsyncClient = Depends(get_client),
    route_cache: RouteCache[RouteSummary] = Depends(get_route_cache),
) -> RouteSummary:
    return await calculate_route_between(
        client,
        Point(lat=from_lat, lon=from_lon),
        Point(lat=to_lat, lon=to_lon),
        EProfile.Foot,
        route_cache,
        include_geometry=geometry,
    )


@router.get("/public-transport")
async def get_public_transport_route_request(
    from_lat: LatQuery,
    from_lon: LonQuery,
    to_lat: LatQuery,
    to_lon: LonQuery,
    radius: RadiusQuery = MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT,
    db: Pool = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_client),
    route_cache: RouteCache[RouteSummary] = Depends(get_route_cache),
) -> RouteSummary:
    return await calculate_public_transport_route_between(
        db,
        client,
        Point(lat=from_lat, lon=from_lon),
        Point(lat=to_lat, lon=to_lon),
        radius,
        MAX_PUBLIC_TRANSPORT_STOPS_TO_CONSIDER,
        route_cache,
    )
