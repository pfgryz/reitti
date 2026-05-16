import httpx
from asyncpg import Pool
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
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/distance", tags=["distance"])


@router.get("/foot")
async def get_foot_route_request(
    client: httpx.AsyncClient = Depends(get_client),
    route_cache: RouteCache[RouteSummary] = Depends(get_route_cache),
    from_lat: float = Query(..., description="From latitude"),
    from_lon: float = Query(..., description="From longitude"),
    to_lat: float = Query(..., description="To latitude"),
    to_lon: float = Query(..., description="To longitude"),
) -> RouteSummary:
    return await calculate_route_between(
        client,
        Point(lat=from_lat, lon=from_lon),
        Point(lat=to_lat, lon=to_lon),
        EProfile.Foot,
        route_cache,
    )


@router.get("/public-transport")
async def get_public_transport_route_request(
    db: Pool = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_client),
    route_cache: RouteCache[RouteSummary] = Depends(get_route_cache),
    from_lat: float = Query(..., description="From latitude"),
    from_lon: float = Query(..., description="From longitude"),
    to_lat: float = Query(..., description="To latitude"),
    to_lon: float = Query(..., description="To longitude"),
    radius: float = Query(
        MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT, description="Radius in meters"
    ),
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
