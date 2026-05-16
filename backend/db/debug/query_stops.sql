SELECT * FROM hsl.routes LIMIT 5;

SELECT * FROM hsl.trips LIMIT 5;

SELECT stop_id, stop_name, ST_AsText(geom)
FROM hsl.stops
LIMIT 5;

SELECT COUNT(1) FROM hsl.routes;
SELECT COUNT(1) FROM hsl.trips;
SELECT COUNT(1) FROM hsl.stops;
SELECT COUNT(1) FROM hsl.stop_times;
SELECT COUNT(1) FROM hsl.stop_pair_avg_time;