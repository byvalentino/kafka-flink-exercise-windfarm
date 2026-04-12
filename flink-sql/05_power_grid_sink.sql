-- =============================================================
-- Lab 4, Step 1: Power & Grid Stats Sink (given)
-- =============================================================
-- Receives 30-second windowed aggregations per farm:
--   total power output, average wind speed, grid frequency stats.
--
-- This is the POWER PRODUCTION & GRID STATUS use case:
--   Grid operators need near-real-time farm-level output
--   to balance supply and demand across the network.
-- =============================================================

CREATE TABLE power_grid_stats (
    farm_id              STRING,
    window_start         TIMESTAMP(3),
    window_end           TIMESTAMP(3),
    total_power_kw       DOUBLE,
    avg_power_kw         DOUBLE,
    avg_wind_speed       DOUBLE,
    max_wind_speed       DOUBLE,
    avg_grid_freq_hz     DOUBLE,
    min_grid_freq_hz     DOUBLE,
    max_grid_freq_hz     DOUBLE,
    turbine_count        BIGINT,
    running_count        BIGINT
) WITH (
    'connector' = 'kafka',
    'topic' = 'power-grid',
    'properties.bootstrap.servers' = 'kafka:29092',
    'format' = 'json'
);
