# Wind Farm Streaming Workshop

## Kafka + Flink for Real-Time Turbine Monitoring

A hands-on, 4-hour workshop. Build a streaming data pipeline that processes wind turbine SCADA telemetry in real time — from raw signals to condition monitoring, asset management, and grid-level power aggregation.

**Cost: $0.** Runs on Docker Compose, locally or via GitHub Codespaces.

**Course:** CE2 — Big Data Management, Lecture 8: Stream Processing (Kafka & Flink)
**Guest Lecture:** Valentino Servizi (Vestas) | **Teacher:** Sokol Kosta | **TA:** Michele Zanitti

---

## The Scenario

Two wind farms produce SCADA (Supervisory Control and Data Acquisition) readings every second from 7 turbines:

| Farm | Type | Turbines | Rated Power |
|------|------|----------|-------------|
| Nordsø-Alpha | Offshore | WTG-NA-01, 02, 03, 04 | 8 MW each |
| Vestjylland-Beta | Onshore | WTG-VB-01, 02, 03 | 3.5 MW each |

**WTG-NA-03** has a degrading main bearing (intermittent vibration spikes — the anomaly you'll detect).
**WTG-VB-02** is in scheduled maintenance (parked, zero output).

Each reading includes: wind speed, rotor RPM, active/reactive power, nacelle vibration, bearing temperature, oil pressure, grid frequency, yaw angle, and operational status.

---

## Architecture

```
  Wind Farms                     Flink Stream Processing
  (SCADA producers)
       │                         ┌─────────────────────────────────┐
       ▼                    ┌───▶│ A. CONDITION MONITORING         │──▶ condition-monitoring
  ┌──────────────┐          │    │    vibration, bearing temp,      │
  │  turbine-    │──────────┤    │    oil pressure → severity       │
  │  signals     │          │    └─────────────────────────────────┘
  │  (raw SCADA) │          │    ┌─────────────────────────────────┐
  └──────────────┘          ├───▶│ B. ASSET MANAGEMENT             │──▶ asset-events
                            │    │    status ≠ 'running' filter     │
                            │    └─────────────────────────────────┘
                            │    ┌─────────────────────────────────┐
                            ├───▶│ C. POWER & GRID (windowed)      │──▶ power-grid
                            │    │    30s farm-level aggregation    │
                            │    └─────────────────────────────────┘
                            │    ┌─────────────────────────────────┐
                            └───▶│ D. ANOMALY DETECTOR (PyFlink)   │──▶ alerts
                                 │    Python UDF, per-turbine logic │
                                 └─────────────────────────────────┘
```

Each output stream serves a different operational function, just as in a real wind farm control center.

---

## Lecture ↔ Workshop Terminology Map

The lecture slides (L8) use general stream processing vocabulary. This workshop uses Kafka- and Flink-specific terms. Here's how they connect:

| Lecture concept (slides) | Workshop equivalent | Where you see it |
|---|---|---|
| **Data stream** (unbounded sequence of tuples) | Kafka topic (`turbine-signals`) | Lab 1: producer → topic → consumer |
| **Tuple / data unit** | Kafka message (one JSON SCADA reading) | Lab 1: each `produce()` call |
| **Message broker** (slides 18-19) | Kafka broker (our `kafka` container) | Lab 1: the middle layer |
| **Topic** (named stream category) | Kafka topic | Lab 1: `turbine-signals`, Lab 2: `condition-monitoring`, etc. |
| **Partition** (parallel sub-log) | Kafka partition (3 per topic) | Lab 1: observe `p=0`, `p=1`, `p=2` in consumer output |
| **Offset** (position in partition log) | Kafka offset | Lab 1: observe `off=42` in consumer output |
| **Consumer group** (load-balanced readers) | Kafka consumer group (`--group` flag) | Lab 1: partition rebalancing experiment |
| **Processing Element / PE** (slides 46-50) | Flink operator (SELECT, CASE WHEN, etc.) | Lab 2: each clause in your SQL is a PE |
| **Data flow graph** (slides 50, 54) | Flink job graph | Lab 2: visible in Flink Dashboard → click running job |
| **Logical plan** (slide 54) | Flink SQL query | Lab 2: your INSERT INTO statement |
| **Physical plan** (slide 54) | Flink execution graph | Lab 2: Flink Dashboard → job → operator chain |
| **Stateless PE** (slide 48) | Condition monitoring filter (no memory between events) | Lab 2: each reading is independent |
| **Stateful PE** (slide 48-49) | Windowed aggregation (accumulates counts/averages) | Lab 4: TUMBLE window maintains state |
| **Event time** (slides 44-47, 63) | `event_time` computed column + WATERMARK | Lab 2: `01_source_table.sql` |
| **Processing time** (slides 44-47) | `NOW()` in Flink SQL | Lab 2: `processed_at` field |
| **Watermark** (slides 67-68, 72-73) | `WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND` | Lab 2: source table definition |
| **Tumbling window** (slides 61-62, 67) | `TUMBLE(TABLE ..., DESCRIPTOR(event_time), INTERVAL '30' SECOND)` | Lab 4: power grid aggregation |
| **Sliding window** (slides 62, 67) | `HOP(TABLE ..., ...)` | Lab 4: bonus challenge |
| **Continuous processing** (slide 42-44) | Flink's record-at-a-time engine | All labs: Flink processes each event individually |
| **Declarative API** (slide 43) | Flink SQL / PyFlink Table API | Lab 2 (SQL), Lab 3 (Python) |
| **Fault tolerance / replication** (slides 38-39, 57) | Kafka partition replication + Flink checkpointing | Lab 4: failure exercise |
| **Backpressure** (slide 56) | Flink Dashboard operator colors | Lab 4: failure exercise experiment 4 |
| **ZooKeeper** (slides 30-32) | **Not used** — our Kafka runs in KRaft mode (see note below) | N/A |

**Note on ZooKeeper vs KRaft:** The lecture slides show the classic Kafka architecture with ZooKeeper for cluster coordination (slide 30-32). Since Kafka 3.3+, KRaft mode replaces ZooKeeper — the coordination logic runs inside Kafka itself. Both do the same job (broker discovery, leader election, offset tracking). Our lab uses KRaft because it's simpler to deploy and is now the default.

**Note on Spark Streaming:** The lecture slides cover Spark Structured Streaming and DStreams (slides 75-86) as a micro-batch approach to stream processing. This workshop uses Apache Flink instead, which is a continuous (record-at-a-time) stream processor. Both are valid approaches. Flink is used here because it provides native stream processing semantics (event time, watermarks, exactly-once) without the micro-batch abstraction layer.

---

## Quick Start

### Option A: GitHub Codespaces (nothing to install)

1. Fork this repo → **Code → Codespaces → Create codespace on main**
2. Wait ~2 min, then: `bash setup-infra.sh`

### Option B: Local Machine

Requires: Docker Desktop, Python 3.9+, Git

```bash
git clone <repo-url> && cd wf-workshop
bash setup-infra.sh
```

**Web UIs:** Kafka UI → http://localhost:8080 | Flink Dashboard → http://localhost:8081

---

## Workshop Schedule

| Time | Block | What You Do |
|------|-------|-------------|
| 0:00–0:15 | **Hook** | Instructor demos the finished pipeline live |
| 0:15–0:45 | **Lab 1** | Build a Kafka producer + consumer (turbine SCADA data) |
| 0:45–1:00 | **Debrief** | Kafka concepts explained through what you just built |
| 1:00–1:15 | **Break** | |
| 1:15–2:00 | **Lab 2** | Write a Flink SQL condition monitoring stream (challenge) |
| 2:00–2:45 | **Lab 3** | Build a PyFlink vibration anomaly detector (challenge) |
| 2:45–3:00 | **Break** | |
| 3:00–3:40 | **Lab 4** | Windowed power aggregation + guided failure exercise |
| 3:40–4:00 | **Wrap-up** | Production patterns, Q&A |

---

## Lab 1: Kafka Basics — Turbine Telemetry

**Goal**: Understand producers, consumers, partitions, and consumer groups using wind turbine data.

### Step 1: Create the topic

```bash
docker exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic turbine-signals --partitions 3 --replication-factor 1
```

### Step 2: Run the producer (Terminal 1)

```bash
python producer.py
```

Watch: 7 turbines across 2 farms producing SCADA readings. Notice how `turbine_id` is used as the message key — all readings from one turbine go to the same partition (ordering guarantee within a partition, slide 36).

### Step 3: Run the consumer (Terminal 2)

```bash
python consumer.py
```

### Step 4: Experiment with consumer groups

```bash
# Second consumer, SAME group → partitions split between them
python consumer.py

# Consumer with DIFFERENT group → both see ALL messages
python consumer.py --group monitoring-team
```

### Step 5: Verify

```bash
python verify/check_lab1.py
```

---

## Lab 2: Flink SQL — Condition Monitoring Stream

**Goal**: Write a Flink SQL query that classifies turbine health from raw SCADA data.

This is the **condition monitoring** use case: a remote operations center watches vibration, bearing temperature, and oil pressure to catch mechanical degradation before a turbine fails.

### Step 1: Create the output topic

```bash
docker exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic condition-monitoring --partitions 3 --replication-factor 1
```

### Step 2: Install the Flink-Kafka connector

```bash
docker exec flink-jobmanager bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar"

docker exec flink-taskmanager bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar"

docker compose restart flink-jobmanager flink-taskmanager
```

### Step 3: Open the Flink SQL Client

```bash
docker exec -it flink-jobmanager ./bin/sql-client.sh
```

### Step 4: Paste the source and sink definitions

Paste the contents of `flink-sql/01_source_table.sql` and `flink-sql/02_cm_sink.sql`.

### Step 5: YOUR CHALLENGE — Write the condition monitoring query

Open `flink-sql/03_challenge_cm.sql`, read the requirements, write the `INSERT INTO` query.

> **Stuck?** Solution: `flink-sql/03_solution_cm.sql`

### Step 6: BONUS — Asset management stream

Paste `flink-sql/04_asset_mgmt.sql` to see how the same source feeds a second functional stream (filtering for non-running turbines). Study how it works — it's given, not a challenge.

### Step 7: Verify

```bash
python verify/check_lab2.py
```

---

## Lab 3: PyFlink — Vibration Anomaly Detector

**Goal**: Build a Python Flink job with a UDF that detects vibration anomalies per turbine.

**Why Python?** SQL can do static thresholds (Lab 2). But real condition monitoring needs per-turbine baselines, multi-signal correlation, or ML model scoring. Python UDFs let you embed that logic inside Flink.

### Step 1: Create the output topic and start PyFlink

```bash
docker exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic alerts --partitions 3 --replication-factor 1

docker compose --profile pyflink up -d --build

docker exec pyflink-runner bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar"
```

### Step 2: YOUR CHALLENGE — Complete the anomaly detector

Edit `pyflink/anomaly_detector.py`: implement the UDF and wire up the pipeline.

### Step 3: Run it

```bash
docker exec -it pyflink-runner python anomaly_detector.py
```

> **Stuck?** Solution: `pyflink/anomaly_detector_solution.py`

### Step 4: Verify

```bash
python verify/check_lab3.py
```

---

## Lab 4: Windowed Aggregation + Failure Exercise

### Part A: Power & Grid Aggregation (20 min)

**Goal**: Compute 30-second farm-level power output and grid frequency stats. This is the **power production & grid status** use case: grid operators need near-real-time farm output to balance supply and demand.

```bash
docker exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic power-grid --partitions 3 --replication-factor 1
```

In the Flink SQL Client, paste `flink-sql/05_power_grid_sink.sql`, then write the windowed aggregation from `flink-sql/06_challenge_power.sql`.

> Solution: `flink-sql/06_solution_power.sql`

```bash
python verify/check_lab4.py
```

### Part B: Guided Failure Exercise (20 min)

With everything running:

```bash
bash failure_exercise.sh
```

This walks you through killing and restarting components. Each experiment maps to lecture concepts (slides referenced in the script).

---

## Project Structure

```
wf-workshop/
├── .devcontainer/devcontainer.json      # GitHub Codespaces
├── flink-sql/
│   ├── 01_source_table.sql              # Given: raw SCADA source
│   ├── 02_cm_sink.sql                   # Given: condition monitoring sink
│   ├── 03_challenge_cm.sql              # ✏️ Challenge: CM transformation
│   ├── 03_solution_cm.sql               # Solution
│   ├── 04_asset_mgmt.sql               # Given: asset management (study example)
│   ├── 05_power_grid_sink.sql           # Given: power/grid sink
│   ├── 06_challenge_power.sql           # ✏️ Challenge: windowed aggregation
│   └── 06_solution_power.sql            # Solution
├── pyflink/
│   ├── anomaly_detector.py              # ✏️ Challenge: vibration anomaly UDF
│   └── anomaly_detector_solution.py     # Solution
├── verify/
│   ├── check_lab1.py                    # Self-check: Kafka basics
│   ├── check_lab2.py                    # Self-check: condition monitoring
│   ├── check_lab3.py                    # Self-check: anomaly detector
│   └── check_lab4.py                    # Self-check: power aggregation
├── docker-compose.yml                   # Local infrastructure-as-code
├── Dockerfile.pyflink                   # PyFlink container
├── producer.py                          # Wind turbine SCADA simulator
├── consumer.py                          # Generic Kafka consumer
├── demo.sh                              # Instructor hook demo
├── setup-infra.sh                       # Start infrastructure
├── rescue.sh                            # Recovery if things break
├── failure_exercise.sh                  # Guided fault-tolerance lab
├── PRODUCTION_MAPPING.md                # Docker Compose → cloud guide
├── requirements.txt
└── README.md
```

---

## Cleanup

```bash
docker compose --profile pyflink down -v
docker system prune -f
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Kafka won't start | `docker logs kafka` — port 9092 conflict? |
| Flink SQL "table not found" | Kafka connector JAR missing — see Lab 2 Step 2 |
| Consumer sees nothing | `--offset earliest` with a new `--group` name |
| Flink job stuck in CREATED | `docker logs flink-taskmanager` — wait or restart |
| PyFlink import error | Run inside `pyflink-runner` container, not on host |
| verify script fails | Read the FAIL message — it tells you exactly what's wrong |
| Everything broken | `bash rescue.sh` |
