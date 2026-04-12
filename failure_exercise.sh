#!/usr/bin/env bash
set -euo pipefail
BOLD="\033[1m" GREEN="\033[92m" YELLOW="\033[93m" RED="\033[91m" CYAN="\033[96m" RESET="\033[0m"

step() { echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n  $*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }
pause() { echo -e "\n  ${YELLOW}▸ Press Enter when you've observed the behavior...${RESET}"; read -r; }
explain() { echo -e "\n  ${GREEN}💡 $*${RESET}"; }

step "EXPERIMENT 1: Kill the Flink TaskManager"
echo -e "
  Imagine a server crash in the condition monitoring center.
  Kafka (the message broker) keeps buffering turbine readings.
  Flink (the stream processor) stops analyzing them.

  ${BOLD}Watch:${RESET}
    - Flink Dashboard: job → RESTARTING
    - Kafka UI: turbine-signals keeps growing, condition-monitoring stops
    - producer.py: still producing (Kafka is independent)
"
pause
echo -e "  ${RED}Killing flink-taskmanager...${RESET}"
docker stop flink-taskmanager
echo -e "  ${RED}✗ TaskManager is DOWN.${RESET}"
echo -e "\n  ${BOLD}OBSERVE for 15-20 seconds, then press Enter.${RESET}"
pause

explain "Kafka decouples turbine data sources from processing.
    Even when the monitoring system is down, no readings are lost.
    This is a key advantage of the broker architecture (slide 19)."

step "EXPERIMENT 2: Bring TaskManager back — checkpoint recovery"
echo -e "
  Flink will:
    1. Restore from its last checkpoint (saved operator state)
    2. Re-read from Kafka at the checkpointed offset
    3. Catch up on all readings that arrived while it was down
    4. Resume real-time processing

  ${BOLD}Watch:${RESET}
    - Flink Dashboard: job → RUNNING
    - condition-monitoring topic: burst of catch-up messages
"
pause
echo -e "  ${GREEN}Restarting flink-taskmanager...${RESET}"
docker start flink-taskmanager
sleep 5
echo -e "  ${GREEN}✓ TaskManager is UP.${RESET}"
echo -e "\n  ${BOLD}OBSERVE the catch-up, then press Enter.${RESET}"
pause

explain "This is Flink's checkpointing in action (stateful processing
    from slide 48). The windowed aggregation (stateful PE) recovers
    its accumulated state. The condition monitoring filter (stateless PE)
    just resumes processing — no state to recover."

step "EXPERIMENT 3: Kill Kafka — everything stops"
echo -e "
  The message broker is the critical dependency.
  In production, Kafka runs 3+ brokers with replication-factor=3
  (slide 39: partition replication). Our lab has one broker.

  ${BOLD}Watch: everything fails.${RESET}
"
pause
echo -e "  ${RED}Killing kafka...${RESET}"
docker stop kafka
echo -e "  ${RED}✗ Kafka is DOWN.${RESET}"
echo -e "\n  ${BOLD}OBSERVE errors for 15 seconds, then press Enter to recover.${RESET}"
pause
echo -e "  ${GREEN}Restarting kafka...${RESET}"
docker start kafka
sleep 15
echo -e "  ${GREEN}✓ Kafka is UP. System self-healing...${RESET}"
pause

explain "In production, Kafka's partition replication (slide 39) means
    one broker dying doesn't affect availability. Our single-broker
    lab is a single point of failure — by design for development."

step "Summary: What You Learned"
echo -e "
  ${BOLD}Key takeaways:${RESET}

  1. ${CYAN}Kafka decouples sources from processors${RESET}
     Turbines keep sending data even when Flink is down.
     (Lecture: message broker architecture, slides 18-19)

  2. ${CYAN}Flink recovers from checkpoints${RESET}
     Stateful operators (windows) restore state.
     Stateless operators (filters) just restart.
     (Lecture: fault-tolerant processing, slides 57-59)

  3. ${CYAN}Kafka replication prevents data loss${RESET}
     Production: 3+ brokers, replication-factor=3.
     (Lecture: partition replication, slide 39)

  4. ${CYAN}Backpressure is visible${RESET}
     Flink Dashboard shows operator health in real time.
     Try: python producer.py --interval 0.05

  ${GREEN}${BOLD}You now understand streaming fault tolerance from experience. 🎓${RESET}
"
