#!/usr/bin/env bash
set -euo pipefail
BOLD="\033[1m" GREEN="\033[92m" YELLOW="\033[93m" RESET="\033[0m"
info()  { echo -e "${GREEN}[✓]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[!]${RESET} $*"; }

echo -e "\n${BOLD}🔧 Rescue: resetting workshop state...${RESET}\n"

TOPICS=("turbine-signals" "condition-monitoring" "asset-events" "power-grid" "alerts")
for topic in "${TOPICS[@]}"; do
    if docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | grep -qw "$topic"; then
        warn "Topic '$topic' exists."
    else
        docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
            --create --topic "$topic" --partitions 3 --replication-factor 1 2>/dev/null
        info "Created topic: $topic"
    fi
done

FLINK_KAFKA_JAR="flink-sql-connector-kafka-3.1.0-1.18.jar"
FLINK_KAFKA_URL="https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/${FLINK_KAFKA_JAR}"
for container in flink-jobmanager flink-taskmanager; do
    if docker exec "$container" test -f "/opt/flink/lib/${FLINK_KAFKA_JAR}" 2>/dev/null; then
        warn "Connector present in $container."
    else
        docker exec "$container" bash -c "cd /opt/flink/lib && curl -sLO ${FLINK_KAFKA_URL}"
        info "Installed connector in $container"
    fi
done

docker compose restart flink-jobmanager flink-taskmanager
sleep 5
info "Flink restarted."

pip install confluent-kafka -q 2>/dev/null || pip install confluent-kafka -q --break-system-packages 2>/dev/null || true

echo -e "\n${GREEN}${BOLD}Rescue complete. You're back on track.${RESET}\n"
