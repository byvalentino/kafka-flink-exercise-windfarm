#!/usr/bin/env python3
"""Lab 2 Verification — Condition Monitoring. Run: python verify/check_lab2.py"""
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

print(f"\n{B}{'='*50}\n  Lab 2: Condition Monitoring Stream\n{'='*50}{RST}\n")

out, _ = run("docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list")
check("Topic 'condition-monitoring' exists", "condition-monitoring" in out,
      "Create: docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 "
      "--create --topic condition-monitoring --partitions 3 --replication-factor 1")

out, _ = run("docker exec flink-jobmanager curl -sf http://localhost:8081/jobs/overview")
check("Flink has a RUNNING job", '"state":"RUNNING"' in (out or ""),
      "Submit your INSERT INTO in the Flink SQL Client")

out, _ = run("docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 "
             "--topic condition-monitoring --from-beginning --timeout-ms 8000 --max-messages 10", timeout=20)
msgs = []
if out:
    for line in out.strip().split("\n"):
        try: msgs.append(json.loads(line))
        except: pass

check("Topic 'condition-monitoring' has messages", len(msgs) > 0,
      "Is producer.py running? Is your INSERT INTO job submitted?")

if msgs:
    m = msgs[0]
    required = ["turbine_id","farm_id","nacelle_vibration_mm_s","bearing_temp_celsius",
                "oil_pressure_bar","severity","original_status"]
    missing = [f for f in required if f not in m]
    check("Messages have all required fields", len(missing) == 0, f"Missing: {missing}")

    if "severity" in m and "nacelle_vibration_mm_s" in m and "bearing_temp_celsius" in m:
        vib, temp = m["nacelle_vibration_mm_s"], m["bearing_temp_celsius"]
        if vib > 10 or temp > 75: expected = "critical"
        elif vib > 5 or temp > 60: expected = "warning"
        else: expected = "normal"
        check(f"Severity is correct (vib={vib:.1f}, temp={temp:.1f} → '{m['severity']}')",
              m["severity"] == expected,
              f"Expected '{expected}'. Check CASE WHEN order: critical first, then warning.")

    devices = set(msg.get("turbine_id") for msg in msgs)
    check(f"Multiple turbines present ({len(devices)} found)", len(devices) >= 2)

print(f"\n{B}{'─'*50}")
if failed == 0: print(f"  {G}All {passed} checks passed! Lab 2 complete. ✓{RST}")
else: print(f"  {passed}/{passed+failed} passed, {R}{failed} failed{RST}")
print(f"{'─'*50}{RST}\n")
sys.exit(0 if failed == 0 else 1)
