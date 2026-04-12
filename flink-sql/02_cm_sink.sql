-- =============================================================
-- Lab 2, Step 2: SINK TABLE — Condition Monitoring (given)
-- =============================================================
-- Receives enriched condition-monitoring data from your
-- transformation query. Each row represents one turbine reading
-- with health indicators and a severity classification.
--
-- Your job in Step 3: write the INSERT INTO query that
-- populates this table from turbine_signals.
-- =============================================================

CREATE TABLE condition_monitoring (
    turbine_id                STRING,
    farm_id                   STRING,
    nacelle_vibration_mm_s    DOUBLE,
    bearing_temp_celsius      DOUBLE,
    oil_pressure_bar          DOUBLE,
    rotor_rpm                 DOUBLE,
    wind_speed_m_s            DOUBLE,
    severity                  STRING,
    original_status           STRING,
    processed_at              TIMESTAMP(3),
    original_ts               STRING
) WITH (
    'connector' = 'kafka',
    'topic' = 'condition-monitoring',
    'properties.bootstrap.servers' = 'kafka:9092',
    'format' = 'json'
);
