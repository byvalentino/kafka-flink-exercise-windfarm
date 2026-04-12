#!/usr/bin/env python3
"""
Wind Farm Kafka Consumer
=========================
Reads from any topic and pretty-prints messages.

Usage:
    python consumer.py                                          # turbine-signals
    python consumer.py --topic condition-monitoring             # CM stream
    python consumer.py --topic power-grid                       # power/grid stream
    python consumer.py --topic asset-events                     # asset mgmt stream
    python consumer.py --group my-group --offset latest

Exercises (Lab 1):
    1. Run two consumers with the SAME --group on 'turbine-signals'.
       → Partitions split between them (consumer group rebalance).

    2. Run two consumers with DIFFERENT --group values.
       → Both see ALL messages (independent consumer groups).

    3. Stop consumer, restart with --offset earliest and a NEW --group.
       → Replays all retained readings from the beginning.
"""

import argparse
import json
import signal

from confluent_kafka import Consumer, KafkaError

# ANSI color by status
STATUS_COLORS = {
    "running": "\033[92m",      # green
    "idle": "\033[93m",         # yellow
    "fault": "\033[91m",        # red
    "maintenance": "\033[95m",  # magenta
}
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def on_assign(consumer, partitions):
    names = [f"p{p.partition}" for p in partitions]
    print(f"\n🔄 Assigned partitions: {names}\n")


def format_message(msg) -> str:
    key = msg.key().decode("utf-8") if msg.key() else "?"
    try:
        v = json.loads(msg.value().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return f"[p={msg.partition()} off={msg.offset()}] (unparseable)"

    status = v.get("status", "?")
    color = STATUS_COLORS.get(status, "")

    # Adapt display based on which topic/fields are present
    turbine = v.get("turbine_id", key)
    farm = v.get("farm_id", "")

    parts = [f"{DIM}[p={msg.partition()} off={msg.offset():>5}]{RESET}"]
    parts.append(f"{color}{turbine:12}{RESET}")

    if "active_power_kw" in v:
        parts.append(f"pwr={BOLD}{v['active_power_kw']:>8.1f}kW{RESET}")
    if "wind_speed_m_s" in v:
        parts.append(f"wind={v['wind_speed_m_s']:>5.1f}m/s")
    if "nacelle_vibration_mm_s" in v:
        vib = v["nacelle_vibration_mm_s"]
        vib_color = "\033[91m" if vib > 5 else ""
        parts.append(f"vib={vib_color}{vib:>6.2f}mm/s{RESET}")
    if "bearing_temp_celsius" in v:
        parts.append(f"bearing={v['bearing_temp_celsius']:>5.1f}°C")
    if "status" in v:
        parts.append(f"{color}{status}{RESET}")
    if "severity" in v:
        sev = v["severity"]
        sev_color = "\033[91m" if sev == "critical" else "\033[93m" if sev == "warning" else ""
        parts.append(f"{sev_color}{sev}{RESET}")

    return "  ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Wind farm Kafka consumer")
    parser.add_argument("--broker", default="localhost:9092")
    parser.add_argument("--topic", default="turbine-signals")
    parser.add_argument("--group", default="lab-consumer-group")
    parser.add_argument("--offset", default="earliest", choices=["earliest", "latest"])
    args = parser.parse_args()

    consumer = Consumer({
        "bootstrap.servers": args.broker,
        "group.id": args.group,
        "auto.offset.reset": args.offset,
        "enable.auto.commit": True,
    })
    consumer.subscribe([args.topic], on_assign=on_assign)

    running = True
    def shutdown(signum, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"📡 Consuming from '{args.topic}'  group='{args.group}'  offset={args.offset}")
    print(f"   Press Ctrl+C to stop.\n")

    count = 0
    try:
        while running:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"❌ Error: {msg.error()}")
                break
            print(format_message(msg))
            count += 1
    finally:
        consumer.close()
        print(f"\n🛑 Closed. Read {count} messages.")


if __name__ == "__main__":
    main()
