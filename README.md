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
git clone <repo-url>
bash setup-infra.sh
```

**Web UIs:** Kafka UI → http://localhost:8080 | Flink Dashboard → http://localhost:8081

---

## Beginner Companion (Read This First)

If you are new to Kafka and Flink, use this section as your "mental map" while doing the labs.

### 1) Why Lab 2 installs three jars

You install three artifacts because they serve different roles:

- `flink-sql-connector-kafka` = SQL table connector wiring (so Flink SQL can read/write Kafka topics)
- `flink-connector-kafka` = runtime implementation used by Flink operators
- `kafka-clients` = Kafka client library used underneath

If one is missing, jobs may compile but fail at runtime with class-not-found style errors.

### 2) `localhost:9092` vs `kafka:29092`

Use this rule:

- From your host terminal (where you run `python producer.py`): use `localhost:9092`
- From inside Docker containers (Flink SQL, Kafka UI, PyFlink): use `kafka:29092`

Think of `localhost` as "outside Docker" and `kafka` as "inside Docker network DNS".

### 3) Event time vs processing time (practical view)

- Event time: uses the timestamp in the message payload. Best for correctness when data can arrive late/out of order.
- Processing time: uses clock time when Flink processes the record. Simpler, but results depend on system timing and delays.

In this workshop, event time is introduced for concept learning, while some exercises may use processing-time-safe patterns to avoid parser/runtime pitfalls in constrained environments.

### 4) What watermarks change

With `WATERMARK ... - INTERVAL '5' SECOND`, Flink assumes records more than ~5s late are "too late" for that event-time window.

Simple intuition:

- late by 2s: usually still counted in the intended window
- late by 8s: likely dropped from that window computation

### 5) Exactly how to run SQL without confusion

When starting a fresh SQL client session, use this order:

1. source table (`01_source_table.sql`)
2. sink table (`02_cm_sink.sql` or `05_power_grid_sink.sql`)
3. your `INSERT INTO` challenge query

If containers restart, assume SQL session state is gone and re-run definitions.

### 6) Consumer group experiment: what to look for

- Same group name in two consumers: each message is processed by one of them (work is split by partitions).
- Different group names: both consumers receive the full stream independently.

You should see different partition ownership behavior, not just different print timing.

### 7) Why PyFlink runs from `pyflink-runner`

The Python script is your job client and logic host. It submits/executes work against the Flink cluster while using Python UDF code.

So:

- SQL labs: launched from SQL client in JobManager
- PyFlink lab: launched from Python container with Flink/Python dependencies

### 8) Failure exercise: what to observe

For each failure/recovery action, record:

1. Kafka topic behavior (producer/consumer continuity)
2. Flink job state transition (`RUNNING`, `RESTARTING`, `FAILED`)
3. Whether output topics continue updating
4. Which lecture concept it maps to (checkpointing, backpressure, fault tolerance)

### 9) Cleanup safety

- `docker compose ... down -v` removes this workshop's containers and named volumes (you lose workshop topic/state data).
- `docker system prune -f` removes unused Docker artifacts globally, which can affect other local projects by deleting stopped containers/images/cache.

If you are unsure, skip prune or inspect with `docker system df` first.

### 10) Suggested solo-study pacing

If studying alone, use this rhythm:

- Lab 1: 30-45 min
- Lab 2: 45-60 min
- Lab 3: 45-75 min
- Lab 4: 45-75 min

If blocked more than 20 min on one step, read the solution, then re-implement from memory once.

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

## Pre-lab Checklist (2 Minutes)

Before starting Lab 1, quickly confirm these basics:

1. Infrastructure is up: run `docker compose ps` and verify `kafka`, `flink-jobmanager`, `flink-taskmanager` are running.
2. Kafka UI opens at `http://localhost:8080`.
3. Flink Dashboard opens at `http://localhost:8081`.
4. Python dependencies are installed: run `python -c "import confluent_kafka; print('ok')"`.
5. Topic tooling responds: run `docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list`.

If any item fails, run `bash setup-infra.sh`. If still broken, run `bash rescue.sh` and re-check.

---

## Lab 1: Kafka Basics — Turbine Telemetry

#### Learning Objective
Build your first producer-consumer system using real turbine data. You will learn how messages flow through Kafka topics, how partitions distribute work, and how consumer groups enable load-balanced reading.

#### How to Achieve It

**Step 1: Create the topic** — Set up a Kafka topic with 3 partitions to distribute turbine readings.

```bash
docker exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --topic turbine-signals --partitions 3 --replication-factor 1
```

**Step 2: Start the producer** — Open Terminal 1 and watch messages flow to Kafka. You should see output like:
```
  ✓ [turbine-signals][p=0] off=42  turbine=WTG-NA-01
```
Each line shows partition assignment and offset — proof that messages arrived.

```bash
python producer.py
```

**Step 3: Start the consumer** — Open Terminal 2. You should immediately see the same messages with full SCADA fields (wind_speed, bearing_temp, status, etc.).

```bash
python consumer.py
```

**Step 4: Understand consumer groups** — This is where Kafka's power shows. Run two more consumers and observe work distribution:

- Same group name: each message is consumed by exactly one (work is partitioned).
- Different group: both get independent replays.

```bash
# Same group → no duplicates, work split by partition
python consumer.py

# Different group → full replay
python consumer.py --group monitoring-team
```

**Step 5: Verify** — Run the verifier to confirm topic setup and message validity.

```bash
python verify/check_lab1.py
```

Expected: All 5 checks pass (✓).

#### If You Get Stuck

- **"Topic already exists"**: Delete and recreate: `docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic turbine-signals`.
- **Consumer shows no messages**: Try: `python consumer.py --offset earliest`.
- **Verify fails on partition count**: Ensure you created with `--partitions 3`.
- **Kafka container won't respond**: Run: `docker logs kafka | tail -20` or execute `bash rescue.sh`.

---

## Lab 2: Flink SQL — Condition Monitoring Stream

#### Learning Objective
Write your first Flink SQL job to transform a raw stream into actionable insights. You will learn how to define streaming tables, apply filtering/classification logic, and understand the difference between reading from Kafka and computing on unbounded streams.

**Context**: Operators at a wind farm need instant alerts when turbines show degradation (high vibration, high bearing temp). Your job classifies each reading as normal, warning, or critical.

#### How to Achieve It

**Step 1: Create the output topic**

```bash
docker exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --topic condition-monitoring --partitions 3 --replication-factor 1
```

**Step 2: Install Flink-Kafka runtime** — Flink needs three jars to connect to Kafka (may take 1-2 min).

```bash
docker exec flink-jobmanager bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar"

docker exec flink-jobmanager bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/3.1.0-1.18/flink-connector-kafka-3.1.0-1.18.jar"

docker exec flink-jobmanager bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.1/kafka-clients-3.5.1.jar"

docker exec flink-taskmanager bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar"

docker exec flink-taskmanager bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/3.1.0-1.18/flink-connector-kafka-3.1.0-1.18.jar"

docker exec flink-taskmanager bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.1/kafka-clients-3.5.1.jar"

docker compose restart flink-jobmanager flink-taskmanager
```

**Step 3: Open Flink SQL Client**

```bash
docker exec -it flink-jobmanager ./bin/sql-client.sh
```

**Step 4: Load source + sink definitions** — Copy-paste entire contents:
- `flink-sql/01_source_table.sql` (raw `turbine_signals` table)
- `flink-sql/02_cm_sink.sql` (output `condition_monitoring` table)

You should see two `[INFO] Execute statement succeed.` confirmations.

**Step 5: Write your challenge** — Open `flink-sql/03_challenge_cm.sql`. Implement an `INSERT INTO condition_monitoring SELECT ...` query that:
- Reads turbine_id, vibration, bearing_temp, oil_pressure, status
- Classifies each as 'normal', 'warning', or 'critical' using CASE WHEN thresholds
- Writes to the sink

Example structure:
```sql
INSERT INTO condition_monitoring
SELECT 
  turbine_id, farm_id,
  CASE 
    WHEN vibration > 5.0 THEN 'critical'
    WHEN bearing_temp > 70 THEN 'warning'
    ELSE 'normal'
  END AS severity,
  ...
FROM turbine_signals;
```

Paste into SQL client. Expect: `[INFO] SQL update statement has been successfully submitted to the cluster:` with a Job ID.

**Step 6: Verify** — Check that alerts flow to the output topic.

```bash
python verify/check_lab2.py
```

Expected: All 6 checks pass (✓).

**Step 7 (BONUS): Study reference** — Paste `flink-sql/04_asset_mgmt.sql` to see how a different functional stream branches off the same source. You won't modify this — just analyze the pattern.

#### If You Get Stuck

- **\"Table not found\"**: You skipped Step 4. Paste `flink-sql/01_source_table.sql` first.
- **Job submitted but no output**: Is the producer running? Start it: `python producer.py` (Lab 1 step 2).
- **Severity values don't match**: Read the verifier error first and re-check your CASE threshold order. Use `flink-sql/03_solution_cm.sql` only as a last-resort sanity check.
- **\"execute statement failed\"**: Syntax error in your query. Copy the solution to see correct CASE WHEN structure.
- **Job stuck in CREATED**: Wait 30s. If persists, check: `docker logs flink-taskmanager | tail -20`.

---

## Lab 3: PyFlink — Vibration Anomaly Detector

#### Learning Objective
Move beyond SQL static rules: build a Python Flink job with a custom UDF (User-Defined Function) that detects bearing anomalies using turbine-specific logic and multi-signal correlation. You will learn how to embed Python inside Flink and submit jobs from a Python client.

**Context**: One turbine (WTG-NA-03) has intermittent bearing degradation. Python UDFs enable per-turbine baselines and temporal patterns that SQL alone cannot express.

#### How to Achieve It

**Step 1: Create output topic and PyFlink container** — Set up the alerts sink and Python runtime (this builds a Docker image; may take 2-3 min).

```bash
docker exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --topic alerts --partitions 3 --replication-factor 1

docker compose --profile pyflink up -d --build

docker exec pyflink-runner bash -c \
  "cd /opt/flink/lib && curl -sLO https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar"
```

**Step 2: Understand the challenge** — Open `pyflink/anomaly_detector.py`. You'll see:
- A `detect_vibration_anomaly()` UDF stub (takes turbine_id, vibration, bearing_temp, status).
- A Flink Table API pipeline stub (reads from `turbine_signals`, applies UDF, filters anomalies, writes to `alerts`).

Your job: implement the UDF to return `True` if an anomaly is detected, else `False`. Use turbine-specific thresholds and multi-signal checks (high vibration + high temp = more likely an issue).

**Step 3: Run your job** — Execute the Python script. It connects to Flink cluster, submits the job, and streams results.

```bash
docker exec -it pyflink-runner python anomaly_detector.py
```

You should see:
```
⚡ Starting vibration anomaly detector...
   Source: turbine-signals → Filter: detect_vibration_anomaly() → Sink: alerts
```

Let it run while you produce data (Step 4).

**Step 4: Send turbine data** — In another terminal, run the producer with a longer burst (~500 readings) so job has time to process anomalies.

```bash
python producer.py --burst 500 --interval 0.5
```

**Step 5: Verify** — Check that anomaly alerts appear, focused on the degraded turbine.

```bash
python verify/check_lab3.py
```

Expected: All 6 checks pass (✓). Most alerts should originate from WTG-NA-03.

#### If You Get Stuck

- **PyFlink build fails**: Check disk space: `docker system df`. If full, run: `docker system prune -f` (warning: deletes orphaned Docker artifacts).
- **\"ModuleNotFoundError: No module named 'pyflink'\"**: Container not built. Re-run: `docker compose --profile pyflink up -d --build`.
- **Job runs but no alerts**: Producer may not be running, or your UDF always returns False. Re-check maintenance filtering and threshold logic first; use `pyflink/anomaly_detector_solution.py` only as a last-resort reference.
- **Verify fails on turbine origin**: Ensure your UDF flags WTG-NA-03's anomalies (should be ~10-20% of its readings).
- **\"address already in use\"**: Previous PyFlink is still running. Stop it: `docker compose --profile pyflink down` and retry Step 1.

---

## Lab 4: Windowed Aggregation + Failure Exercise

### Part A: Power & Grid Windowed Aggregation

#### Learning Objective
Build your first streaming aggregation job. You will learn how Flink maintains state over time windows, groups data by farm, and emits periodic summaries. This is crucial for real-time dashboards and SLA monitoring.

**Context**: Grid operators need farm-level power summaries every 30 seconds (not per-turbine detail). Your job tumbles the continuous turbine stream into 30-second windows, computes totals/averages per farm, and emits one output record per window.

#### How to Achieve It

**Step 1: Create output topic** — Grid operators will listen to this feed.

```bash
docker exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --topic power-grid --partitions 3 --replication-factor 1
```

**Step 2: Open Flink SQL Client** (if you closed it).

```bash
docker exec -it flink-jobmanager ./bin/sql-client.sh
```

If reusing an existing session from Lab 2, you already have tables defined. Otherwise, paste `flink-sql/01_source_table.sql` and `flink-sql/05_power_grid_sink.sql`.

**Step 3: Load sink definition** — Paste `flink-sql/05_power_grid_sink.sql` to define the output table and Kafka routing.

**Step 4: Write your windowed aggregation** — Open `flink-sql/06_challenge_power.sql`. Implement an `INSERT INTO power_grid_stats` query that:
- Groups by farm_id
- Tumbles time into 30-second windows
- Computes SUM, AVG, MIN/MAX for power, wind speed, grid frequency
- Counts total readings and "running" status

Example structure:
```sql
INSERT INTO power_grid_stats
SELECT
  farm_id,
  window_start,
  window_end,
  ROUND(SUM(active_power_kw), 1) AS total_power_kw,
  ROUND(AVG(active_power_kw), 1) AS avg_power_kw,
  ...
FROM TABLE(
  TUMBLE(TABLE ..., DESCRIPTOR(...), INTERVAL '30' SECOND)
)
GROUP BY farm_id, window_start, window_end;
```

Paste into SQL client. Expect: Job ID confirmation.

**Step 5: Produce data** — Run a long burst (~350 readings) so multiple windows fire.

```bash
python producer.py --burst 350 --interval 0.8
```

**Step 6: Verify** — Check that windowed summaries flow to Kafka.

```bash
python verify/check_lab4.py
```

Expected: All 7 checks pass (✓), including validation that both farms have aggregated records.

#### If You Get Stuck

- **\"RowTime field should not be null\"**: Event-time parsing failed. Use processing-time windows (see solution) or clean timestamps.
- **\"Table not found\"**: You skipped loading the sink. Paste `flink-sql/05_power_grid_sink.sql`.
- **Job submitted but no output**: Producer may not be running, or windows haven't closed yet. Run producer for >40s so a second window fires. Then check output: `docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic power-grid --from-beginning --max-messages 5`.
- **Verify fails on fields**: Your aggregation likely has a schema mismatch. Re-check sink column order and aliases first; use `flink-sql/06_solution_power.sql` only as a last-resort reference.

---

### Part B: Guided Failure Exercise

#### Learning Objective
Understand how distributed streaming systems handle component failures: broker crashes, job restarts, state recovery. Each failure experiment maps directly to lecture concepts (checkpointing, replication, fault tolerance).

#### How to Achieve It

With everything still running from Part A (producer ongoing, Flink jobs active), run the failure exercise:

```bash
bash failure_exercise.sh
```

The script guides you through deliberate failures like:
- Stopping Kafka broker → see producer/consumer pause.
- Killing a Flink TaskManager → see job restart and state recovery.
- Network partition → see backpressure and buffering.

Each step references lecture slides where the concept was introduced.

#### If You Get Stuck

- **\"Cannot connect to Kafka\"**: This is expected during Kafka shutdown. Let the script continue — recovery is part of the demo.
- **Flink jobs stuck in RESTARTING**: Wait 20-30s for TaskManager recovery. If persists, check: `docker logs flink-taskmanager | tail -30`.
- **Don't know what to observe**: Record: job state (RUNNING → RESTARTING → RUNNING), checkpoint lag, topic lag. Compare before/after each fault.
- **Unsure about lecture connection**: Each experiment step prints the relevant slide number.

---

## Project Structure

Solution files are included for fallback/self-study after you've attempted each challenge.

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
