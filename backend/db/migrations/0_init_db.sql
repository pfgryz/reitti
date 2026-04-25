DROP SCHEMA IF EXISTS hsl CASCADE;

CREATE SCHEMA IF NOT EXISTS hsl;

CREATE TABLE IF NOT EXISTS hsl.routes (
    route_id TEXT PRIMARY KEY,
    agency_id TEXT,
    route_short_name TEXT,
    route_long_name TEXT,
    route_desc TEXT,
    route_type TEXT,
    route_url TEXT
);

CREATE TABLE IF NOT EXISTS hsl.trips (
    route_id TEXT,
    service_id TEXT,
    trip_id TEXT PRIMARY KEY,
    trip_headsign TEXT,
    direction_id INT,
    shape_id TEXT,
    wheelchair_accessible INT,
    bikes_allowed INT,
    max_delay INT,
    
    CONSTRAINT fk_trips_route
        FOREIGN KEY (route_id) REFERENCES hsl.routes(route_id)
);

CREATE TABLE IF NOT EXISTS hsl.stops (
    stop_id TEXT PRIMARY KEY,
    stop_code TEXT,
    stop_name TEXT,
    stop_desc TEXT,
    stop_lat DOUBLE PRECISION,
    stop_lon DOUBLE PRECISION,
    zone_id TEXT,
    stop_url TEXT,
    location_type INT,
    parent_station TEXT,
    wheelchair_boarding INT,
    platform_code TEXT,
    vehicle_type INT,
    digistop_id TEXT,
    CONSTRAINT fk_stops_parent
        FOREIGN KEY (parent_station) REFERENCES hsl.stops(stop_id)
);

CREATE TABLE IF NOT EXISTS hsl.stop_times (
    trip_id TEXT,
    arrival_time TEXT,
    departure_time TEXT,
    stop_id TEXT,
    stop_sequence INT,
    stop_headsign TEXT,
    pickup_type INT,
    drop_off_type INT,
    shape_dist_traveled DOUBLE PRECISION,
    timepoint INT,
    PRIMARY KEY (trip_id, stop_sequence),
    CONSTRAINT fk_stop_times_trip
        FOREIGN KEY (trip_id) REFERENCES hsl.trips(trip_id),
    CONSTRAINT fk_stop_times_stop
        FOREIGN KEY (stop_id) REFERENCES hsl.stops(stop_id)
);