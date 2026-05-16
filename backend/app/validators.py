from typing import Annotated

from config import MAX_STOPS_QUERY_COUNT
from fastapi import Query

LatQuery = Annotated[float, Query(..., ge=-90, le=90, description="Latitude")]
LonQuery = Annotated[float, Query(..., ge=-180, le=180, description="Longitude")]
CountQuery = Annotated[
    int,
    Query(ge=1, le=MAX_STOPS_QUERY_COUNT, description="Number of stops to return"),
]
RequiredRadiusQuery = Annotated[
    float, Query(..., gt=0, le=5000, description="Radius in meters")
]
RadiusQuery = Annotated[float, Query(gt=0, le=5000, description="Radius in meters")]
