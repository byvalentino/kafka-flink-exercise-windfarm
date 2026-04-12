-- =============================================================
-- Lab 4, Step 2: SOLUTION — Farm Power & Grid Aggregation
-- =============================================================

CREATE TEMPORARY VIEW turbine_signals_proc AS
SELECT
    farm_id,
    active_power_kw,
    wind_speed_m_s,
    grid_frequency_hz,
    status,
    PROCTIME() AS proc_time
FROM turbine_signals
WHERE `timestamp` IS NOT NULL;

INSERT INTO power_grid_stats
SELECT
    farm_id,
    window_start,
    window_end,
    ROUND(SUM(active_power_kw), 1)                             AS total_power_kw,
    ROUND(AVG(active_power_kw), 1)                             AS avg_power_kw,
    ROUND(AVG(wind_speed_m_s), 2)                              AS avg_wind_speed,
    ROUND(MAX(wind_speed_m_s), 2)                              AS max_wind_speed,
    ROUND(AVG(grid_frequency_hz), 3)                           AS avg_grid_freq_hz,
    ROUND(MIN(grid_frequency_hz), 3)                           AS min_grid_freq_hz,
    ROUND(MAX(grid_frequency_hz), 3)                           AS max_grid_freq_hz,
    COUNT(*)                                                   AS turbine_count,
    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END)       AS running_count
FROM TABLE(
    TUMBLE(
        TABLE turbine_signals_proc,
        DESCRIPTOR(proc_time),
        INTERVAL '30' SECOND
    )
)
GROUP BY farm_id, window_start, window_end;
