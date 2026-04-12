-- =============================================================
-- Lab 2 BONUS: Asset Management Stream
-- =============================================================
-- This filters for non-running turbines and status transitions,
-- producing a feed for the asset management system.
--
-- This is given as a WORKING EXAMPLE to study, not a challenge.
-- It shows how the same source can feed multiple functional streams.
-- =============================================================

CREATE TABLE asset_events (
    turbine_id         STRING,
    farm_id            STRING,
    status             STRING,
    wind_speed_m_s     DOUBLE,
    active_power_kw    DOUBLE,
    event_time_str     STRING,
    logged_at          TIMESTAMP(3)
) WITH (
    'connector' = 'kafka',
    'topic' = 'asset-events',
    'properties.bootstrap.servers' = 'kafka:29092',
    'format' = 'json'
);

-- Only forward readings where the turbine is NOT running normally
INSERT INTO asset_events
SELECT
    turbine_id,
    farm_id,
    status,
    wind_speed_m_s,
    active_power_kw,
    `timestamp`        AS event_time_str,
    NOW()              AS logged_at
FROM turbine_signals
WHERE status <> 'running';
