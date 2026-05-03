from asyncpg import Pool
from core.routing import Point
from pydantic import BaseModel


class Stop(BaseModel):
    name: str
    lat: float
    lon: float


async def get_nearest_stop(db: Pool, lat: float, lon: float) -> Stop:
    return (await get_nearest_stops(db, lat, lon, count=1))[0]


async def get_nearest_stops(db: Pool, point: Point, count: int = 10) -> list[Stop]:
    rows = await db.fetch(
        """
        SELECT
            stop_name AS name,
            stop_lat AS lat,
            stop_lon AS lon
        FROM hsl.stops
        WHERE geom IS NOT NULL
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
        LIMIT $3
        """,
        point.lon,
        point.lat,
        count,
    )

    return [Stop(name=row["name"], lat=row["lat"], lon=row["lon"]) for row in rows]


async def get_nearest_stops_in_radius(
    db: Pool, point: Point, radius: float, count: int = 10
) -> list[Stop]:
    rows = await db.fetch(
        """
        SELECT  
            stop_name AS name,
            stop_lat as lat,
            stop_lon as lon
        FROM hsl.stops
        WHERE geom IS NOT NULL
        AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3)
        ORDER BY ST_Distance(geom, ST_SetSRID(ST_MakePoint($1, $2), 4326)) ASC
        LIMIT $4
        """,
        point.lon,
        point.lat,
        radius,
        count,
    )

    return [Stop(name=row["name"], lat=row["lat"], lon=row["lon"]) for row in rows]
