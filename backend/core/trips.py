from asyncpg import Pool
from pydantic import BaseModel

from core.stops import Stop


class StopsTrip(BaseModel):
    from_stop: Stop
    to_stop: Stop
    average_travel_time: float


def gtfs_time_to_seconds_sql(column: str) -> str:
    return f"""(
        split_part({column}, ':', 1)::int * 3600
        + split_part({column}, ':', 2)::int * 60
        + split_part({column}, ':', 3)::int
    )"""


async def get_average_trips_between_stops_groups(
    db: Pool, from_stops: list[Stop], to_stops: list[Stop], limit: int = 100
) -> list[StopsTrip]:
    if not from_stops or not to_stops:
        return []

    from_stops_ids = {stop.id: stop for stop in from_stops}
    to_stops_ids = {stop.id: stop for stop in to_stops}

    dep_sec = gtfs_time_to_seconds_sql("st_from.departure_time")
    arr_sec = gtfs_time_to_seconds_sql("st_to.arrival_time")

    rows = await db.fetch(
        f"""
        WITH legs AS (
            SELECT
                st_from.stop_id AS from_stop_id,
                st_to.stop_id AS to_stop_id,
                CASE
                    WHEN {arr_sec} >= {dep_sec} THEN {arr_sec} - {dep_sec}
                    ELSE {arr_sec} + 86400 - {dep_sec}
                END AS duration_seconds
            FROM hsl.stop_times st_from
            INNER JOIN hsl.stop_times st_to
                ON st_from.trip_id = st_to.trip_id
                AND st_from.stop_sequence < st_to.stop_sequence
            WHERE st_from.stop_id = ANY($1::text[])
                AND st_to.stop_id = ANY($2::text[])
                AND st_from.departure_time ~ '^[0-9]+:[0-9]{{2}}:[0-9]{{2}}$'
                AND st_to.arrival_time ~ '^[0-9]+:[0-9]{{2}}:[0-9]{{2}}$'
        )
        SELECT 
            from_stop_id,
            to_stop_id,
            AVG(duration_seconds)::double precision AS average_travel_time
        FROM legs
        WHERE duration_seconds >= 0
        GROUP BY from_stop_id, to_stop_id
        ORDER BY average_travel_time ASC, from_stop_id, to_stop_id
        LIMIT $3
        """,
        [stop.id for stop in from_stops],
        [stop.id for stop in to_stops],
        limit,
    )

    result: list[StopsTrip] = []
    for row in rows:
        from_id = row["from_stop_id"]
        to_id = row["to_stop_id"]
        avg_time = row["average_travel_time"]

        if from_id not in from_stops_ids or to_id not in to_stops_ids:
            continue
        if avg_time is None:
            continue

        result.append(
            StopsTrip(
                from_stop=from_stops_ids[from_id],
                to_stop=to_stops_ids[to_id],
                average_travel_time=float(avg_time),
            )
        )

    return result
