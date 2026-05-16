CREATE INDEX IF NOT EXISTS idx_stop_times_stop_id
    ON hsl.stop_times (stop_id);

CREATE INDEX IF NOT EXISTS idx_stop_times_trip_sequence
    ON hsl.stop_times (trip_id, stop_sequence);
