#!/usr/bin/env python3
"""
Wind Farm SCADA Producer
=========================
Simulates real-time telemetry from wind turbines across multiple farms.
Each turbine produces a SCADA reading every interval with:

  - Environmental: wind_speed, wind_direction
  - Mechanical: rotor_rpm, nacelle_vibration, bearing_temp, oil_pressure, yaw_angle
  - Electrical: active_power_kw, reactive_power_kvar, grid_frequency_hz
  - Operational: status (running, idle, fault, maintenance)

All readings go to the 'turbine-signals' topic. Flink then routes them
into functional streams (condition monitoring, asset management, power/grid).

Usage:
    python producer.py                         # defaults
    python producer.py --broker kafka:9092     # custom broker
    python producer.py --interval 1.0          # one reading per second
    python producer.py --burst 100             # produce 100 then stop

Domain model:
    Farm "Nordsø-Alpha"   → 4 offshore turbines (WTG-NA-01..04)
    Farm "Vestjylland-Beta" → 3 onshore turbines  (WTG-VB-01..03)

    WTG-NA-03 has a degrading main bearing (intermittent vibration spikes).
    WTG-VB-02 is in scheduled maintenance (status='maintenance', no power).
"""

import argparse
import json
import math
import random
import signal
import time
from datetime import datetime, timezone

from confluent_kafka import Producer

TOPIC = "turbine-signals"

# ── Wind Farm Configuration ──────────────────────────────────────────

FARMS = {
    "Nordsø-Alpha": {
        "type": "offshore",
        "turbines": {
            "WTG-NA-01": {"rated_power_kw": 8000, "status": "running"},
            "WTG-NA-02": {"rated_power_kw": 8000, "status": "running"},
            "WTG-NA-03": {"rated_power_kw": 8000, "status": "running",
                          "bearing_degradation": True},  # faulty turbine
            "WTG-NA-04": {"rated_power_kw": 8000, "status": "running"},
        },
    },
    "Vestjylland-Beta": {
        "type": "onshore",
        "turbines": {
            "WTG-VB-01": {"rated_power_kw": 3500, "status": "running"},
            "WTG-VB-02": {"rated_power_kw": 3500, "status": "maintenance"},
            "WTG-VB-03": {"rated_power_kw": 3500, "status": "running"},
        },
    },
}

# ── Physics-ish simulation ───────────────────────────────────────────

# Shared wind conditions per farm (slowly drifting)
_farm_wind = {}


def _get_farm_wind(farm_id: str) -> float:
    """Simulate slowly varying wind speed per farm (5-25 m/s)."""
    if farm_id not in _farm_wind:
        _farm_wind[farm_id] = random.uniform(8, 14)
    # Random walk: drift ±0.3 m/s per reading, clamped to [3, 28]
    _farm_wind[farm_id] += random.gauss(0, 0.3)
    _farm_wind[farm_id] = max(3.0, min(28.0, _farm_wind[farm_id]))
    return _farm_wind[farm_id]


def _power_curve(wind_speed: float, rated_kw: float) -> float:
    """Simplified power curve: cubic below rated, flat at rated, zero above cut-out."""
    cut_in, rated_ws, cut_out = 3.5, 12.0, 25.0
    if wind_speed < cut_in or wind_speed > cut_out:
        return 0.0
    if wind_speed >= rated_ws:
        return rated_kw
    # Cubic region
    fraction = ((wind_speed - cut_in) / (rated_ws - cut_in)) ** 3
    return rated_kw * fraction


def generate_reading(farm_id: str, turbine_id: str, config: dict) -> dict:
    """Generate one SCADA reading for a turbine."""
    status = config["status"]
    rated = config["rated_power_kw"]

    wind_speed = _get_farm_wind(farm_id) + random.gauss(0, 0.5)
    wind_speed = max(0.0, wind_speed)
    wind_direction = (270 + random.gauss(0, 15)) % 360  # prevailing westerlies

    if status == "maintenance":
        # Turbine is parked — zero output, minimal signals
        return {
            "turbine_id": turbine_id,
            "farm_id": farm_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "wind_speed_m_s": round(wind_speed, 2),
            "wind_direction_deg": round(wind_direction, 1),
            "rotor_rpm": 0.0,
            "active_power_kw": 0.0,
            "reactive_power_kvar": 0.0,
            "nacelle_vibration_mm_s": round(random.gauss(0.3, 0.05), 3),
            "bearing_temp_celsius": round(random.gauss(22, 1), 1),
            "oil_pressure_bar": round(random.gauss(2.0, 0.1), 2),
            "grid_frequency_hz": round(random.gauss(50.0, 0.02), 3),
            "yaw_angle_deg": round(wind_direction + random.gauss(0, 2), 1),
            "status": "maintenance",
        }

    # Running or idle turbine
    power = _power_curve(wind_speed, rated)
    is_producing = power > 0

    # RPM correlates with wind speed (up to ~15 rpm at rated)
    rotor_rpm = (wind_speed / 12.0) * 15.0 if is_producing else 0.0
    rotor_rpm = max(0, rotor_rpm + random.gauss(0, 0.3))

    # Vibration: normally 1-3 mm/s, but WTG-NA-03 has bearing issues
    base_vib = 1.5 + (power / rated) * 1.0  # load-dependent
    if config.get("bearing_degradation") and random.random() < 0.12:
        base_vib += random.uniform(5, 15)  # anomaly spike
    vibration = max(0.1, base_vib + random.gauss(0, 0.2))

    # Bearing temperature: 35-55°C when running, correlated with load
    bearing_temp = 35 + (power / rated) * 18 + random.gauss(0, 1.5)
    if config.get("bearing_degradation") and vibration > 5:
        bearing_temp += random.uniform(5, 15)  # overheating with vibration

    # Oil pressure: 3-5 bar normally
    oil_pressure = 3.5 + (power / rated) * 1.0 + random.gauss(0, 0.15)

    # Grid frequency: 50 Hz ± small variation
    grid_freq = 50.0 + random.gauss(0, 0.03)

    # Yaw tracks wind direction with some lag
    yaw = wind_direction + random.gauss(0, 3)

    # Reactive power: ~10-20% of active, can go negative
    reactive = power * random.uniform(0.08, 0.22) * random.choice([1, -1])

    # Status: running if producing, idle if wind too low/high
    actual_status = "running" if is_producing else "idle"

    # Rare fault event on the degraded turbine
    if config.get("bearing_degradation") and vibration > 12:
        actual_status = "fault"

    return {
        "turbine_id": turbine_id,
        "farm_id": farm_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "wind_speed_m_s": round(wind_speed, 2),
        "wind_direction_deg": round(wind_direction, 1),
        "rotor_rpm": round(rotor_rpm, 2),
        "active_power_kw": round(power + random.gauss(0, power * 0.02 + 1), 1),
        "reactive_power_kvar": round(reactive, 1),
        "nacelle_vibration_mm_s": round(vibration, 3),
        "bearing_temp_celsius": round(bearing_temp, 1),
        "oil_pressure_bar": round(oil_pressure, 2),
        "grid_frequency_hz": round(grid_freq, 3),
        "yaw_angle_deg": round(yaw, 1),
        "status": actual_status,
    }


# ── Kafka delivery ───────────────────────────────────────────────────

def on_delivery(err, msg):
    if err:
        print(f"  ✗ Failed: {err}")
    else:
        key = msg.key().decode() if msg.key() else "?"
        print(
            f"  ✓ [{msg.topic()}][p={msg.partition()}] "
            f"off={msg.offset()}  turbine={key}"
        )


def main():
    parser = argparse.ArgumentParser(description="Wind turbine SCADA producer")
    parser.add_argument("--broker", default="localhost:9092")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Seconds between readings per turbine cycle (default: 1.0)")
    parser.add_argument("--topic", default=TOPIC)
    parser.add_argument("--burst", type=int, default=0,
                        help="Produce N readings then stop (0 = infinite)")
    args = parser.parse_args()

    producer = Producer({
        "bootstrap.servers": args.broker,
        "client.id": "windfarm-scada",
        "linger.ms": 50,
        "batch.size": 32768,
        "acks": "all",
        "enable.idempotence": True,
    })

    running = True
    def shutdown(signum, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Build flat turbine list
    turbines = []
    for farm_id, farm in FARMS.items():
        for tid, cfg in farm["turbines"].items():
            turbines.append((farm_id, tid, cfg))

    print(f"⚡ Wind Farm SCADA Producer")
    print(f"   Broker: {args.broker}")
    print(f"   Topic:  {args.topic}")
    print(f"   Farms:  {list(FARMS.keys())}")
    print(f"   Turbines: {[t[1] for t in turbines]}")
    print(f"   Interval: {args.interval}s per cycle")
    if args.burst:
        print(f"   Mode: burst ({args.burst} readings)")
    print(f"   Press Ctrl+C to stop.\n")

    count = 0
    try:
        while running:
            for farm_id, tid, cfg in turbines:
                reading = generate_reading(farm_id, tid, cfg)

                producer.produce(
                    topic=args.topic,
                    key=reading["turbine_id"],  # partition by turbine
                    value=json.dumps(reading),
                    callback=on_delivery,
                )
                producer.poll(0)
                count += 1

                if args.burst and count >= args.burst:
                    break

            if args.burst and count >= args.burst:
                break

            if count % 35 == 0:  # every 5 cycles (7 turbines × 5)
                print(f"\n--- {count} readings produced ---\n")

            time.sleep(args.interval)
    finally:
        remaining = producer.flush(timeout=5)
        print(f"\n🛑 Done. Produced {count} readings ({remaining} unflushed).")


if __name__ == "__main__":
    main()
