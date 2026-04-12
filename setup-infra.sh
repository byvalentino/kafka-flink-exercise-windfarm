#!/usr/bin/env bash
set -euo pipefail
BOLD="\033[1m" GREEN="\033[92m" YELLOW="\033[93m" RED="\033[91m" RESET="\033[0m"
info()  { echo -e "${GREEN}[✓]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[!]${RESET} $*"; }
error() { echo -e "${RED}[✗]${RESET} $*"; exit 1; }

echo -e "\n${BOLD}Starting wind farm infrastructure...${RESET}\n"
docker compose up -d

echo "Waiting for Kafka..."
for i in $(seq 1 30); do
    docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list &>/dev/null && { info "Kafka ready."; break; }
    [ "$i" -eq 30 ] && error "Kafka did not start. Run: docker logs kafka"
    sleep 2
done

echo "Waiting for Flink..."
for i in $(seq 1 20); do
    docker exec flink-jobmanager curl -sf http://localhost:8081/overview &>/dev/null && { info "Flink ready."; break; }
    [ "$i" -eq 20 ] && warn "Flink may not be ready — check http://localhost:8081"
    sleep 2
done

pip install confluent-kafka -q 2>/dev/null || pip install confluent-kafka -q --break-system-packages 2>/dev/null || true
info "Python kafka client installed."

echo -e "\n${GREEN}${BOLD}Infrastructure ready!${RESET}"
echo -e "  Kafka UI:        ${BOLD}http://localhost:8080${RESET}"
echo -e "  Flink Dashboard: ${BOLD}http://localhost:8081${RESET}"
echo -e "\n  Next: follow the lab instructions in README.md\n"
