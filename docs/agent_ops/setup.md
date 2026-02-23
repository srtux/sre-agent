# Setting up Agent Graph Observability

The SRE Agent uses a specialized "Agent Graph" to visualize the execution paths, tool invocations, and LLM reasoning of agents in real-time. This is powered by Google Cloud Observability and BigQuery.

This guide outlines the setup process and the required IAM permissions.

## Architecture Overview

1. **Cloud Observability Bucket**: Agent spans and traces are exported from the application using OpenTelemetry to a Google Cloud Observability Bucket.
2. **Linked BigQuery Dataset**: The Observability bucket is linked to a BigQuery dataset (typically named `traces`), automatically synchronizing telemetry data.
3. **Agent Graph Schema**: The SRE Agent executes schema modeling over the raw traces to build materialized views (`_AllSpans`, `agent_spans_raw`, `nodes`, `edges`, etc.) within an `agent_graph` BigQuery dataset.

### Automatic Dataset Discovery

To simplify multi-project support, the SRE Agent backend automatically discovers linked datasets:
- **Traces**: Scans Cloud Observability buckets for datasets linked to the `Spans` path. Used for the topology graph and evaluation service.
- **Logs**: Scans the Cloud Logging `_Default` bucket for BigQuery links. Used for correlated log viewing in the Trace Details panel.

Discovery is cached for 1 hour to optimize performance.

## Automated Setup Wizard

The AgentOps UI provides an automated onboarding wizard that handles this entire process. You simply need to navigate to the Agent Ops Dashboard.

If the setup is incomplete, the wizard will intercept the view and guide you through the following phases:

1. **Observability Bucket Validation**: Verifies the existence of an Observability bucket in the current GCP project.
2. **Dataset Linking**: Prompts to create and link a BigQuery dataset to the bucket if one doesn't exist. This kicks off a Long Running Operation (LRO) in GCP.
3. **BigQuery Verification**: Polling to ensure the linked dataset and its base `_AllSpans` view are fully accessible.
4. **Schema Execution**: Idempotently executes the sequence of BigQuery commands required to build the graph models.

## Required IAM Permissions

For the automated setup wizard to successfully configure your project, the identity running the backend SRE Agent needs the following IAM roles:

| Action | Required Role(s) | Notes |
| :--- | :--- | :--- |
| **Check Observability Bucket** | `roles/observability.viewer` or `roles/observability.admin` | Read access to list buckets. |
| **Link BigQuery Dataset** | `roles/observability.admin` AND (`roles/bigquery.admin` OR `roles/bigquery.dataEditor`) | Linking requires management access to Cloud Observability *and* permission to create the target BigQuery dataset. |
| **Verify BigQuery Dataset** | `roles/bigquery.dataViewer` | Read access to the linked dataset. |
| **Execute Schema Steps**<br>(Create Datasets/Views/Tables) | `roles/bigquery.dataEditor` | Write access to create the `agent_graph` dataset and materialize views from the `traces` dataset. |

### Troubleshooting 403 Forbidden Errors

If the setup wizard encounters a `403 Forbidden` error during any phase, it will halt and display the exact IAM role(s) required.
1. Open the [Google Cloud IAM Console](https://console.cloud.google.com/iam-admin/iam).
2. Grant the required role(s) to the Service Account used by the SRE Agent backend.
3. Click "Retry" in the wizard. The setup process is idempotent and will resume.

## Manual Setup via API

If you prefer to integrate the setup into CI/CD pipelines, you can call the backend endpoints sequentially:

1. `GET /api/v1/graph/setup/check_bucket?project_id=<id>`
2. `POST /api/v1/graph/setup/link_dataset`
3. Poll `GET /api/v1/graph/setup/lro_status?project_id=<id>&operation_name=<name>`
4. Poll `GET /api/v1/graph/setup/verify?project_id=<id>`
5. Sequentially POST to `/api/v1/graph/setup/schema/{step}` for each of the following steps: `create_dataset`, `cleanup`, `agent_spans_raw`, `nodes`, `edges`, `trajectories`, `graph`, `hourly`, `backfill`, `registries`.
