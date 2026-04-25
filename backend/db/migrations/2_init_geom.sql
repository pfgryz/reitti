ALTER TABLE hsl.stops
ADD COLUMN geom geometry(Point, 4326);

UPDATE hsl.stops
SET GEOM = ST_SetSRID(St_MakePoint(stop_lon, stop_lat), 4326)
WHERE stop_lon IS NOT NULL AND stop_lat IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_stops_geom
ON hsl.stops
USING GIST (geom);