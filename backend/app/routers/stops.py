from typing import List

from asyncpg import Pool
from core.db import get_db
from core.stops import Stop, get_nearest_stops
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("/nearest")
async def get_nearest_stops_request(
    db: Pool = Depends(get_db),
    lat: float = Query(..., description="Latitude of the location"),
    lon: float = Query(..., description="Longitude of the location"),
    count: int = Query(1, description="Number of stops to return"),
) -> List[Stop]:
    return await get_nearest_stops(db, lat, lon, count)
