TRUNCATE hsl.routes, hsl.trips, hsl.stops, hsl.stop_times RESTART IDENTITY;

-- routess
COPY hsl.routes
FROM '/gtfs/routes.txt'
WITH (FORMAT csv, HEADER true);

-- trips
COPY hsl.trips
FROM '/gtfs/trips.txt'
WITH (FORMAT csv, HEADER true);

-- stops
CREATE TEMP TABLE tmp_stops (LIKE hsl.stops INCLUDING DEFAULTS);

COPY tmp_stops
FROM '/gtfs/stops.txt'
WITH (FORMAT csv, HEADER true);

INSERT INTO hsl.stops (
    stop_id, stop_code, stop_name, stop_desc, stop_lat, stop_lon, zone_id, stop_url, location_type, 
    parent_station, wheelchair_boarding, platform_code, vehicle_type, digistop_id
)
SELECT
    stop_id, stop_code, stop_name, stop_desc, stop_lat, stop_lon, zone_id, stop_url, location_type,
    NULLIF(BTRIM(parent_station), ''),
    wheelchair_boarding, platform_code, vehicle_type, digistop_id
FROM tmp_stops;

-- stop times
COPY hsl.stop_times
FROM '/gtfs/stop_times.txt'
WITH (FORMAT csv, HEADER true);