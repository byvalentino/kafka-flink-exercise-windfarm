-- =============================================================
-- Lab 2, Step 3: SOLUTION — Don't peek until you've tried!
-- =============================================================

INSERT INTO condition_monitoring
SELECT
    turbine_id,
    farm_id,
    nacelle_vibration_mm_s,
    bearing_temp_celsius,
    oil_pressure_bar,
    rotor_rpm,
    wind_speed_m_s,
    CASE
        WHEN nacelle_vibration_mm_s > 10.0 OR bearing_temp_celsius > 75.0
            THEN 'critical'
        WHEN nacelle_vibration_mm_s > 5.0  OR bearing_temp_celsius > 60.0
            THEN 'warning'
        ELSE 'normal'
    END                     AS severity,
    status                  AS original_status,
    NOW()                   AS processed_at,
    `timestamp`             AS original_ts
FROM turbine_signals;
