CREATE TABLE IF NOT EXISTS hsl.stop_pair_avg_time (
    from_stop_id TEXT NOT NULL,
    to_stop_id TEXT NOT NULL,
    average_travel_time DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (from_stop_id, to_stop_id)
);

TRUNCATE hsl.stop_pair_avg_time;

INSERT INTO hsl.stop_pair_avg_time (from_stop_id, to_stop_id, average_travel_time)
WITH legs AS (
    SELECT
        st_from.stop_id AS from_stop_id,
        st_to.stop_id AS to_stop_id,
        CASE
            WHEN (
                split_part(st_to.arrival_time, ':', 1)::int * 3600
                + split_part(st_to.arrival_time, ':', 2)::int * 60
                + split_part(st_to.arrival_time, ':', 3)::int
            ) >= (
                split_part(st_from.departure_time, ':', 1)::int * 3600
                + split_part(st_from.departure_time, ':', 2)::int * 60
                + split_part(st_from.departure_time, ':', 3)::int
            ) THEN (
                split_part(st_to.arrival_time, ':', 1)::int * 3600
                + split_part(st_to.arrival_time, ':', 2)::int * 60
                + split_part(st_to.arrival_time, ':', 3)::int
            ) - (
                split_part(st_from.departure_time, ':', 1)::int * 3600
                + split_part(st_from.departure_time, ':', 2)::int * 60
                + split_part(st_from.departure_time, ':', 3)::int
            )
            ELSE (
                split_part(st_to.arrival_time, ':', 1)::int * 3600
                + split_part(st_to.arrival_time, ':', 2)::int * 60
                + split_part(st_to.arrival_time, ':', 3)::int
            ) + 86400 - (
                split_part(st_from.departure_time, ':', 1)::int * 3600
                + split_part(st_from.departure_time, ':', 2)::int * 60
                + split_part(st_from.departure_time, ':', 3)::int
            )
        END AS duration_seconds
    FROM hsl.stop_times st_from
    INNER JOIN hsl.stop_times st_to
        ON st_from.trip_id = st_to.trip_id
        AND st_from.stop_sequence < st_to.stop_sequence
    WHERE st_from.departure_time ~ '^[0-9]+:[0-9]{2}:[0-9]{2}$'
        AND st_to.arrival_time ~ '^[0-9]+:[0-9]{2}:[0-9]{2}$'
)
SELECT
    from_stop_id,
    to_stop_id,
    AVG(duration_seconds)::double precision
FROM legs
WHERE duration_seconds >= 0
GROUP BY from_stop_id, to_stop_id;

DROP INDEX IF EXISTS hsl.idx_stop_pair_avg_from_id;
DROP INDEX IF EXISTS hsl.idx_stop_pair_avg_to_id;

CREATE INDEX idx_stop_pair_avg_from_id
    ON hsl.stop_pair_avg_time (from_stop_id);

CREATE INDEX idx_stop_pair_avg_to_id
    ON hsl.stop_pair_avg_time (to_stop_id);
