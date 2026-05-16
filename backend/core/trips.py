from asyncpg import Pool
from pydantic import BaseModel

from core.stops import Stop


class StopsTrip(BaseModel):
    from_stop: Stop
    to_stop: Stop
    average_travel_time: float


async def get_average_trips_between_stops_groups(
    db: Pool, from_stops: list[Stop], to_stops: list[Stop], limit: int = 100
) -> list[StopsTrip]:
    if not from_stops or not to_stops:
        return []

    from_stops_ids = {stop.id: stop for stop in from_stops}
    to_stops_ids = {stop.id: stop for stop in to_stops}

    rows = await db.fetch(
        """
        SELECT
            from_stop_id,
            to_stop_id,
            average_travel_time
        FROM hsl.stop_pair_avg_time
        WHERE from_stop_id = ANY($1::text[])
            AND to_stop_id = ANY($2::text[])
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
