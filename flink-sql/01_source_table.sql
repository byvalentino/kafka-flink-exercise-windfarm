-- =============================================================
-- Lab 2, Step 1: SOURCE TABLE (given — paste this as-is)
-- =============================================================
-- Maps the 'turbine-signals' Kafka topic to a Flink SQL table.
-- Every SCADA reading from every turbine becomes a row.
--
-- Key concepts:
--   - 'timestamp' needs backticks (SQL reserved word)
--   - event_time is a COMPUTED COLUMN: parsed from the ISO string
--   - WATERMARK allows up to 5s of late/out-of-order data
--
-- In lecture terms:
--   - This table is a Processing Element (PE) source
--   - The watermark defines how Flink handles event-time skew
-- =============================================================

CREATE TABLE turbine_signals (
    turbine_id                STRING,
    farm_id                   STRING,
    `timestamp`               STRING,
    wind_speed_m_s            DOUBLE,
    wind_direction_deg        DOUBLE,
    rotor_rpm                 DOUBLE,
    active_power_kw           DOUBLE,
    reactive_power_kvar       DOUBLE,
    nacelle_vibration_mm_s    DOUBLE,
    bearing_temp_celsius      DOUBLE,
    oil_pressure_bar          DOUBLE,
    grid_frequency_hz         DOUBLE,
    yaw_angle_deg             DOUBLE,
    status                    STRING,

    -- Computed column: parse ISO timestamp into Flink TIMESTAMP
    event_time AS TO_TIMESTAMP(`timestamp`),

    -- Watermark: tolerate up to 5 seconds of late data
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'turbine-signals',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-windfarm',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json',
    'json.fail-on-missing-field' = 'false',
    'json.ignore-parse-errors' = 'true'
);

-- Sanity check (run if producer.py is active):
-- SELECT turbine_id, active_power_kw, nacelle_vibration_mm_s, status
-- FROM turbine_signals LIMIT 10;
