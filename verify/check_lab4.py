#!/usr/bin/env python3
"""Lab 4 Verification — Power & Grid Aggregation. Run: python verify/check_lab4.py"""
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

print(f"\n{B}{'='*50}\n  Lab 4: Power & Grid Windowed Aggregation\n{'='*50}{RST}\n")

out, _ = run("docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list")
check("Topic 'power-grid' exists", "power-grid" in out)

out, _ = run("docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 "
             "--topic power-grid --from-beginning --timeout-ms 12000 --max-messages 10", timeout=20)
msgs = []
if out:
    for line in out.strip().split("\n"):
        try: msgs.append(json.loads(line))
        except: pass

check("Topic 'power-grid' has windowed results", len(msgs) > 0,
      "Producer must run >30s and your windowed INSERT INTO must be submitted.")

if msgs:
    m = msgs[0]
    required = ["farm_id","window_start","window_end","total_power_kw",
                "avg_power_kw","avg_wind_speed","turbine_count","running_count"]
    missing = [f for f in required if f not in m]
    check("Messages have all required fields", len(missing) == 0, f"Missing: {missing}")

    if "total_power_kw" in m and "avg_power_kw" in m and "turbine_count" in m:
        tc = m["turbine_count"]
        check(f"Turbine count is positive ({tc})", tc > 0)
        if tc > 0:
            expected_total = m["avg_power_kw"] * tc
            check("total_power_kw ≈ avg × count (within 20%)",
                  abs(m["total_power_kw"] - expected_total) < expected_total * 0.2 + 1,
                  f"total={m['total_power_kw']}, avg={m['avg_power_kw']}, count={tc}")

    if "avg_grid_freq_hz" in m:
        check(f"Grid frequency near 50 Hz ({m['avg_grid_freq_hz']:.3f})",
              49.8 < m["avg_grid_freq_hz"] < 50.2)

    farms = set(msg.get("farm_id") for msg in msgs)
    check(f"Results from multiple farms ({sorted(farms)})", len(farms) >= 2,
          "Run producer.py longer to get windows from both farms.")

print(f"\n{B}{'─'*50}")
if failed == 0: print(f"  {G}All {passed} checks passed! Lab 4 complete. ✓{RST}")
else: print(f"  {passed}/{passed+failed} passed, {R}{failed} failed{RST}")
print(f"{'─'*50}{RST}\n")
sys.exit(0 if failed == 0 else 1)
