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

FLINK_KAFKA_SQL_JAR="flink-sql-connector-kafka-3.1.0-1.18.jar"
FLINK_KAFKA_SQL_URL="https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/${FLINK_KAFKA_SQL_JAR}"
FLINK_KAFKA_RUNTIME_JAR="flink-connector-kafka-3.1.0-1.18.jar"
FLINK_KAFKA_RUNTIME_URL="https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/3.1.0-1.18/${FLINK_KAFKA_RUNTIME_JAR}"
KAFKA_CLIENTS_JAR="kafka-clients-3.5.1.jar"
KAFKA_CLIENTS_URL="https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.1/${KAFKA_CLIENTS_JAR}"
for container in flink-jobmanager flink-taskmanager; do
    if docker exec "$container" test -f "/opt/flink/lib/${FLINK_KAFKA_SQL_JAR}" 2>/dev/null; then
        warn "${FLINK_KAFKA_SQL_JAR} present in $container."
    else
        docker exec "$container" bash -c "cd /opt/flink/lib && curl -sLO ${FLINK_KAFKA_SQL_URL}"
        info "Installed ${FLINK_KAFKA_SQL_JAR} in $container"
    fi

    if docker exec "$container" test -f "/opt/flink/lib/${FLINK_KAFKA_RUNTIME_JAR}" 2>/dev/null; then
        warn "${FLINK_KAFKA_RUNTIME_JAR} present in $container."
    else
        docker exec "$container" bash -c "cd /opt/flink/lib && curl -sLO ${FLINK_KAFKA_RUNTIME_URL}"
        info "Installed ${FLINK_KAFKA_RUNTIME_JAR} in $container"
    fi

    if docker exec "$container" test -f "/opt/flink/lib/${KAFKA_CLIENTS_JAR}" 2>/dev/null; then
        warn "${KAFKA_CLIENTS_JAR} present in $container."
    else
        docker exec "$container" bash -c "cd /opt/flink/lib && curl -sLO ${KAFKA_CLIENTS_URL}"
        info "Installed ${KAFKA_CLIENTS_JAR} in $container"
    fi
done

docker compose restart flink-jobmanager flink-taskmanager
sleep 5
info "Flink restarted."

pip install confluent-kafka -q 2>/dev/null || pip install confluent-kafka -q --break-system-packages 2>/dev/null || true

echo -e "\n${GREEN}${BOLD}Rescue complete. You're back on track.${RESET}\n"
