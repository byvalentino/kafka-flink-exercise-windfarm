#!/usr/bin/env python3
"""Lab 1 Verification — Kafka Basics. Run: python verify/check_lab1.py"""
import json, subprocess, sys

G, R, Y, B, RST = "\033[92m", "\033[91m", "\033[93m", "\033[1m", "\033[0m"
passed = failed = 0

def check(name, ok, detail=""):
    global passed, failed
    if ok: print(f"  {G}✓ PASS{RST}  {name}"); passed += 1
    else:
        msg = f"  {R}✗ FAIL{RST}  {name}"
        if detail: msg += f"\n         {Y}{detail}{RST}"
        print(msg); failed += 1

def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired: return "", 1

print(f"\n{B}{'='*50}\n  Lab 1: Kafka Basics (Wind Farm)\n{'='*50}{RST}\n")

out, _ = run("docker ps --filter name=kafka --format '{{.Names}}'")
check("Kafka container is running", "kafka" in out, "Run: docker compose up -d")

out, _ = run("docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list")
check("Topic 'turbine-signals' exists", "turbine-signals" in out,
      "Create: docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 "
      "--create --topic turbine-signals --partitions 3 --replication-factor 1")

out, _ = run("docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 "
             "--describe --topic turbine-signals")
check("Topic has 3+ partitions", out.count("Partition:") >= 3)

out, _ = run("docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 "
             "--topic turbine-signals --from-beginning --timeout-ms 5000 --max-messages 1", timeout=15)
has_msg = False
if out:
    try:
        msg = json.loads(out.split("\n")[0])
        has_msg = "turbine_id" in msg and "active_power_kw" in msg
    except: pass
check("Topic has valid turbine readings", has_msg,
      "Run producer.py: python producer.py --burst 30")

if has_msg:
    check("Reading has wind farm fields",
          all(k in msg for k in ["farm_id","wind_speed_m_s","nacelle_vibration_mm_s","bearing_temp_celsius"]))

print(f"\n{B}{'─'*50}")
if failed == 0: print(f"  {G}All {passed} checks passed! Lab 1 complete. ✓{RST}")
else: print(f"  {passed}/{passed+failed} passed, {R}{failed} failed{RST}")
print(f"{'─'*50}{RST}\n")
sys.exit(0 if failed == 0 else 1)
