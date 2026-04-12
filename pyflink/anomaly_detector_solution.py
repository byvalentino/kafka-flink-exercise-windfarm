#!/usr/bin/env python3
"""Lab 3 SOLUTION — Don't peek until you've tried anomaly_detector.py!"""

from pyflink.table import EnvironmentSettings, TableEnvironment
from pyflink.table.udf import udf
from pyflink.table.expressions import col, lit, call

env_settings = EnvironmentSettings.in_streaming_mode()
t_env = TableEnvironment.create(env_settings)
t_env.get_config().set("parallelism.default", "2")
t_env.get_config().set(
    "pipeline.jars",
    "file:///opt/flink/lib/flink-sql-connector-kafka-3.1.0-1.18.jar"
)

@udf(result_type='BOOLEAN')
def detect_vibration_anomaly(
    turbine_id: str, vibration: float, bearing_temp: float, status: str
) -> bool:
    if status == "maintenance":
        return False
    # Offshore 8MW turbines have higher baseline vibration
    threshold = 4.0 if turbine_id.startswith("WTG-NA") else 3.5
    if vibration > threshold:
        return True
    # Correlated: moderate vibration + elevated bearing temperature
    if vibration > 3.0 and bearing_temp > 65.0:
        return True
    return False

t_env.create_temporary_function("detect_vibration_anomaly", detect_vibration_anomaly)

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
        status                 STRING,
        event_time AS TO_TIMESTAMP(`timestamp`),
        WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'turbine-signals',
        'properties.bootstrap.servers' = 'kafka:9092',
        'properties.group.id' = 'pyflink-vibration-solution',
        'scan.startup.mode' = 'earliest-offset',
        'format' = 'json',
        'json.ignore-parse-errors' = 'true'
    )
""")

t_env.execute_sql("""
    CREATE TABLE alerts (
        turbine_id             STRING,
        farm_id                STRING,
        nacelle_vibration_mm_s DOUBLE,
        bearing_temp_celsius   DOUBLE,
        active_power_kw        DOUBLE,
        status                 STRING,
        original_ts            STRING,
        detected_at            TIMESTAMP(3)
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'alerts',
        'properties.bootstrap.servers' = 'kafka:9092',
        'format' = 'json'
    )
""")

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
        col("`timestamp`").alias("original_ts"),
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
        lit(None).cast("TIMESTAMP(3)").alias("detected_at")
    )

result.execute_insert("alerts").wait()
