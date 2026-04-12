#!/usr/bin/env python3
"""
Lab 3 — PyFlink Challenge: Turbine Vibration Anomaly Detector
==============================================================
YOUR TASK: Build a Python Flink job that reads from 'turbine-signals',
applies a Python UDF for vibration anomaly detection, and writes
alerts to the 'alerts' topic.

WHY PYTHON (not just SQL)??
  SQL CASE WHEN is fine for static thresholds, but real condition
  monitoring needs logic that SQL can't express:
    - Per-turbine historical baselines
    - Multi-signal correlation (vibration + temperature together)
    - ML model scoring
    - Lookups against maintenance databases
  This lab shows how Python UDFs let you embed that logic in Flink.

Run inside the PyFlink container:
    docker compose --profile pyflink up -d --build
    docker exec -it pyflink-runner python anomaly_detector.py

Requirements:
    1. Read from 'turbine-signals' topic
    2. Apply the detect_vibration_anomaly() UDF
    3. Only forward events where the UDF returns True
    4. Write alerts to 'alerts' topic

When done, run (from host): python verify/check_lab3.py
"""

from pyflink.table import EnvironmentSettings, TableEnvironment
from pyflink.table.udf import udf
from pyflink.table.expressions import col, lit, call

# ── Environment setup ────────────────────────────────────────────────
env_settings = EnvironmentSettings.in_streaming_mode()
t_env = TableEnvironment.create(env_settings)
t_env.get_config().set("parallelism.default", "2")
t_env.get_config().set(
    "pipeline.jars",
    "file:///opt/flink/lib/flink-sql-connector-kafka-3.1.0-1.18.jar"
)


# ── YOUR UDF ─────────────────────────────────────────────────────────
# This function runs IN Python for every turbine reading.
# In production, this could call a trained ML model, check a
# maintenance database, or compute a rolling statistical baseline.

@udf(result_type='BOOLEAN')
def detect_vibration_anomaly(
    turbine_id: str,
    vibration: float,
    bearing_temp: float,
    status: str,
) -> bool:
    """
    Returns True if the turbine reading indicates a vibration anomaly.

    YOUR LOGIC HERE. Suggested approach:

    1. Different turbine types have different normal vibration ranges:
       - Offshore 8MW turbines (WTG-NA-*): normal < 4.0 mm/s
       - Onshore 3.5MW turbines (WTG-VB-*): normal < 3.5 mm/s

    2. A reading is anomalous if:
       - Vibration exceeds the turbine-type threshold, OR
       - Vibration > 3.0 AND bearing_temp > 65 (correlated failure)

    3. Ignore readings from turbines in maintenance (status == 'maintenance')
    """
    if status == "maintenance":
        return False

    threshold = 4.0 if turbine_id.startswith("WTG-NA") else 3.5
    if vibration > threshold:
        return True
    if vibration > 3.0 and bearing_temp > 65.0:
        return True
    return False


t_env.create_temporary_function("detect_vibration_anomaly", detect_vibration_anomaly)


# ── Source table ─────────────────────────────────────────────────────
t_env.execute_sql("""
    CREATE TABLE turbine_signals (
        turbine_id             STRING,
        farm_id                STRING,
        `timestamp`            STRING,
        wind_speed_m_s         DOUBLE,
        rotor_rpm              DOUBLE,
        active_power_kw        DOUBLE,
        nacelle_vibration_mm_s DOUBLE,
        bearing_temp_celsius   DOUBLE,
        oil_pressure_bar       DOUBLE,
        status                 STRING
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'turbine-signals',
        'properties.bootstrap.servers' = 'kafka:29092',
        'properties.group.id' = 'pyflink-vibration-detector',
        'scan.startup.mode' = 'earliest-offset',
        'format' = 'json',
        'json.ignore-parse-errors' = 'true'
    )
""")


# ── Sink table ───────────────────────────────────────────────────────
t_env.execute_sql("""
    CREATE TABLE alerts (
        turbine_id             STRING,
        farm_id                STRING,
        nacelle_vibration_mm_s DOUBLE,
        bearing_temp_celsius   DOUBLE,
        active_power_kw        DOUBLE,
        status                 STRING,
        original_ts            STRING,
        detected_at            STRING
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'alerts',
        'properties.bootstrap.servers' = 'kafka:29092',
        'format' = 'json'
    )
""")


# ── Pipeline ─────────────────────────────────────────────────────────
print("⚡ Starting vibration anomaly detector...")
print("   Source: turbine-signals → Filter: detect_vibration_anomaly() → Sink: alerts")
print("   Press Ctrl+C to stop.\n")

result = t_env.from_path("turbine_signals") \
    .select(
        col("turbine_id"),
        col("farm_id"),
        col("nacelle_vibration_mm_s"),
        col("bearing_temp_celsius"),
        col("active_power_kw"),
        col("status"),
           col("timestamp").alias("original_ts"),
        call("detect_vibration_anomaly",
             col("turbine_id"),
             col("nacelle_vibration_mm_s"),
             col("bearing_temp_celsius"),
             col("status"),
        ).alias("is_anomaly")
    ) \
    .filter(col("is_anomaly") == lit(True)) \
    .select(
        col("turbine_id"),
        col("farm_id"),
        col("nacelle_vibration_mm_s"),
        col("bearing_temp_celsius"),
        col("active_power_kw"),
        col("status"),
        col("original_ts"),
        col("original_ts").alias("detected_at")
    )

result.execute_insert("alerts").wait()
