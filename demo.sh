#!/usr/bin/env bash
set -euo pipefail
BOLD="\033[1m" GREEN="\033[92m" CYAN="\033[96m" YELLOW="\033[93m" RESET="\033[0m"
step() { echo -e "\n${CYAN}${BOLD}▸ $*${RESET}"; }
RULE=$(printf '%*s' 60 '' | tr ' ' '=')

echo -e "\n${BOLD}${RULE}\n  🎬  LIVE DEMO: Wind Farm Streaming Pipeline\n${RULE}${RESET}\n"

step "Producing 40 turbine SCADA readings..."
python producer.py --burst 40 --interval 0.05 2>/dev/null
echo -e "  ${GREEN}✓${RESET} 40 readings from 7 turbines across 2 wind farms"

step "Raw turbine data in Kafka..."
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 \
    --topic turbine-signals --from-beginning --max-messages 2 --timeout-ms 3000 2>/dev/null || true

step "Condition monitoring output (if Flink jobs running)..."
CM=$(docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 \
    --topic condition-monitoring --from-beginning --timeout-ms 3000 --max-messages 2 2>/dev/null || true)
if [ -n "$CM" ]; then echo "$CM"
else echo -e "  ${YELLOW}Not yet — you'll build this in Lab 2!${RESET}"; fi

step "Power grid aggregations (if windowed job running)..."
PG=$(docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 \
    --topic power-grid --from-beginning --timeout-ms 3000 --max-messages 2 2>/dev/null || true)
if [ -n "$PG" ]; then echo "$PG"
else echo -e "  ${YELLOW}Not yet — you'll build this in Lab 4!${RESET}"; fi

echo -e "\n${BOLD}${RULE}\n  📋  Today's Pipeline Architecture\n${RULE}${RESET}"
cat << 'EOF'

  Wind Farms                     Flink Processing Layer
  (SCADA producers)
       │                         ┌─────────────────────────────┐
       ▼                    ┌───▶│ A. Condition Monitoring     │──▶ condition-monitoring
  ┌──────────────┐          │    │    vibration + temp → severity│
  │  turbine-    │──────────┤    └─────────────────────────────┘
  │  signals     │          │    ┌─────────────────────────────┐
  │  (all SCADA) │          ├───▶│ B. Asset Management         │──▶ asset-events
  └──────────────┘          │    │    non-running status filter │
                            │    └─────────────────────────────┘
                            │    ┌─────────────────────────────┐
                            ├───▶│ C. Power & Grid (windowed)  │──▶ power-grid
                            │    │    30s farm-level aggregation│
                            │    └─────────────────────────────┘
                            │    ┌─────────────────────────────┐
                            └───▶│ D. PyFlink Anomaly Detector │──▶ alerts
                                 │    Python UDF per turbine   │
                                 └─────────────────────────────┘

  Lab 1: Build the left side (Kafka producer + consumer)
  Lab 2: Build stream A (Flink SQL condition monitoring)
  Lab 3: Build stream D (PyFlink anomaly detector)
  Lab 4: Build stream C (windowed power aggregation) + break things

EOF
echo -e "${GREEN}${BOLD}  Let's start building! ⚡${RESET}\n"
