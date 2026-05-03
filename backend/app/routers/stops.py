from typing import List

from asyncpg import Pool
from core import Point
from core.dependencies import get_db
from core.stops import Stop, get_nearest_stops, get_nearest_stops_in_radius
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("/nearest")
async def get_nearest_stops_request(
    db: Pool = Depends(get_db),
    lat: float = Query(..., description="Latitude of the location"),
    lon: float = Query(..., description="Longitude of the location"),
    count: int = Query(1, description="Number of stops to return"),
) -> List[Stop]:
    return await get_nearest_stops(db, Point(lat=lat, lon=lon), count)


@router.get("/nearest-in-radius")
async def get_nearest_stops_in_radius_request(
    db: Pool = Depends(get_db),
    lat: float = Query(..., description="Latitude of the location"),
    lon: float = Query(..., description="Longitude of the location"),
    radius: float = Query(..., description="Radius in meters"),
    count: int = Query(1, description="Number of stops to return"),
) -> List[Stop]:
    return await get_nearest_stops_in_radius(db, Point(lat=lat, lon=lon), radius, count)
