import httpx
from core.dependencies import get_client
from core.routing import EProfile, Point, RouteSummary, calculate_route_between
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/distance", tags=["distance"])


@router.get("/foot")
async def get_foot_distance(
    client: httpx.AsyncClient = Depends(get_client),
    from_lon: float = Query(..., description="From longitude"),
    from_lat: float = Query(..., description="From latitude"),
    to_lon: float = Query(..., description="To longitude"),
    to_lat: float = Query(..., description="To latitude"),
) -> RouteSummary:
    return await calculate_route_between(
        client,
        Point(lon=from_lon, lat=from_lat),
        Point(lon=to_lon, lat=to_lat),
        EProfile.Foot,
    )
