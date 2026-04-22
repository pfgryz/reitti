from typing import List

from core.stops import Stop
from fastapi import APIRouter, Query

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("/nearest")
async def get_nearest_stops(
    lat: float = Query(..., description="Latitude of the location"),
    lon: float = Query(..., description="Longitude of the location"),
    count: int = Query(1, description="Number of stops to return"),
) -> List[Stop]:
    return await get_nearest_stops(lat, lon, count)
