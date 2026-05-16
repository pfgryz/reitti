from typing import List

from asyncpg import Pool
from app.validators import CountQuery, LatQuery, LonQuery, RequiredRadiusQuery
from core import Point
from core.dependencies import get_db
from core.stops import Stop, get_nearest_stops, get_nearest_stops_in_radius
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("/nearest")
async def get_nearest_stops_request(
    lat: LatQuery,
    lon: LonQuery,
    count: CountQuery = 1,
    db: Pool = Depends(get_db),
) -> List[Stop]:
    return await get_nearest_stops(db, Point(lat=lat, lon=lon), count)


@router.get("/nearest-in-radius")
async def get_nearest_stops_in_radius_request(
    lat: LatQuery,
    lon: LonQuery,
    radius: RequiredRadiusQuery,
    count: CountQuery = 1,
    db: Pool = Depends(get_db),
) -> List[Stop]:
    return await get_nearest_stops_in_radius(db, Point(lat=lat, lon=lon), radius, count)
