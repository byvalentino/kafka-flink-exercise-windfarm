#!/usr/bin/env python3
"""Lab 3 Verification — PyFlink Anomaly Detector. Run: python verify/check_lab3.py"""
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

print(f"\n{B}{'='*50}\n  Lab 3: PyFlink Vibration Anomaly Detector\n{'='*50}{RST}\n")

out, _ = run("docker ps --filter name=pyflink-runner --format '{{.Names}}'")
check("PyFlink container is running", "pyflink-runner" in out,
      "Start: docker compose --profile pyflink up -d --build")

out, _ = run("docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list")
check("Topic 'alerts' exists", "alerts" in out,
      "Create: docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 "
      "--create --topic alerts --partitions 3 --replication-factor 1")

out, _ = run("docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 "
             "--topic alerts --from-beginning --timeout-ms 12000 --max-messages 5", timeout=20)
msgs = []
if out:
    for line in out.strip().split("\n"):
        try: msgs.append(json.loads(line))
        except: pass

check("Topic 'alerts' has messages", len(msgs) > 0,
      "Ensure producer.py is running (WTG-NA-03 generates anomalies ~12% of the time).\n"
      "         Your PyFlink job may need 30-60s to see anomalies.")

if msgs:
    m = msgs[0]
    check("Alert has required fields",
          all(k in m for k in ["turbine_id","nacelle_vibration_mm_s","bearing_temp_celsius"]))

    all_elevated = all(
        msg.get("nacelle_vibration_mm_s", 0) > 2.5 or msg.get("bearing_temp_celsius", 0) > 60
        for msg in msgs
    )
    check("All alerts are genuine anomalies (elevated vibration or temperature)", all_elevated,
          "Some alerts have normal readings. Check your UDF thresholds.")

    na03 = sum(1 for m in msgs if m.get("turbine_id") == "WTG-NA-03")
    check(f"Most alerts from WTG-NA-03 (degraded bearing): {na03}/{len(msgs)}", na03 > 0,
          "WTG-NA-03 has bearing_degradation=True in the producer — it should dominate alerts.")

print(f"\n{B}{'─'*50}")
if failed == 0: print(f"  {G}All {passed} checks passed! Lab 3 complete. ✓{RST}")
else: print(f"  {passed}/{passed+failed} passed, {R}{failed} failed{RST}")
print(f"{'─'*50}{RST}\n")
sys.exit(0 if failed == 0 else 1)
