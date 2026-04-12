# From Docker Compose to Production Cloud IaC

This workshop uses Docker Compose as **local infrastructure-as-code**. Here's an honest
comparison with production cloud equivalents, and a wind-energy specific context.

## What Docker Compose gives you

- Declarative service definitions (what to run, how to configure)
- Reproducible environments (anyone with the file gets the same setup)
- Dependency ordering and health checks
- Network isolation and volume management

## What Docker Compose does NOT give you

- State tracking / drift detection (no "what changed since last apply")
- Cloud resource provisioning (VMs, managed services, IAM, networking)
- Multi-environment management (dev / staging / production)
- Secret management, compliance, cost control

## Production equivalents

| Workshop (Docker Compose) | Azure (Terraform/Bicep) | AWS (Terraform/CDK) |
|---|---|---|
| `kafka` (Bitnami) | Azure Event Hubs (Kafka protocol) | Amazon MSK |
| `kafka-ui` | Confluent Control Center | MSK Console |
| `flink-jobmanager` | Azure HDInsight Flink | Amazon Managed Flink |
| `flink-taskmanager` | (managed by HDInsight) | (managed) |
| `docker-compose.yml` | `main.tf` + `variables.tf` | `main.tf` or CDK stack |

## Wind energy context

In a real Vestas/Siemens Gamesa/Ørsted deployment, the architecture maps to:

| Workshop component | Production equivalent |
|---|---|
| `producer.py` | SCADA gateway on each wind farm, pushing to Kafka via VPN/satellite |
| `turbine-signals` topic | One topic per signal group, partitioned by farm or turbine |
| Flink condition monitoring job | Runs in a dedicated K8s cluster, 24/7 monitoring |
| `alerts` topic | Feeds into PagerDuty / ServiceNow for operator dispatch |
| `power-grid` aggregation | Feeds into grid operator APIs (e.g., Energinet in Denmark) |

The application code (producer, Flink SQL, PyFlink UDFs) stays nearly identical.
You change the broker address, add TLS/SASL authentication, and deploy via CI/CD.
