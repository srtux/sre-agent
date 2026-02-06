"""Provision a Conversational Analytics (CA) Data Agent for Auto SRE.

This script creates (or updates) a CA Data Agent named 'ca-autosre' that is
connected to the BigQuery telemetry tables in the target project.  It also
grants the necessary IAM roles to the agent's service account.

Usage:
    python deploy/setup_ca_agent.py --project-id MY_PROJECT

Prerequisites:
    pip install google-cloud-geminidataanalytics

The script will:
1. Discover BigQuery datasets containing _AllSpans / _AllLogs tables
2. Create a CA Data Agent connected to those tables
3. Grant the required IAM roles for the service account

Environment variables:
    GOOGLE_CLOUD_LOCATION  - Region (default: 'global')
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_AGENT_ID = "ca-autosre"
DEFAULT_LOCATION = "global"

SYSTEM_INSTRUCTION = """\
You are CA-AutoSRE, a data analytics assistant specialising in Site Reliability
Engineering.  You have access to BigQuery tables containing distributed traces
(_AllSpans) and application logs (_AllLogs) exported from Cloud Observability.

When answering questions:
- Default to the last 1 hour of data unless the user specifies otherwise.
- Include concrete numbers (counts, p50/p99 latencies, error rates).
- When a chart would help, generate one automatically.
- Use span_name, service_name, status_code, and duration columns for traces.
- Use severity, json_payload, and timestamp columns for logs.
"""


def run_gcloud(cmd: list[str], exit_on_fail: bool = True) -> str:
    """Run a gcloud command and return stdout."""
    full = ["gcloud", *cmd]
    logger.info(f"  $ {' '.join(full)}")
    result = subprocess.run(full, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed: {result.stderr.strip()}")
        if exit_on_fail:
            sys.exit(1)
    return result.stdout.strip()


def discover_bq_tables(project_id: str) -> list[dict[str, str]]:
    """Discover _AllSpans and _AllLogs tables via bq CLI."""
    logger.info("Discovering BigQuery telemetry tables...")
    datasets_raw = run_gcloud(
        [
            "alpha",
            "bq",
            "datasets",
            "list",
            f"--project={project_id}",
            "--format=value(datasetId)",
        ],
        exit_on_fail=False,
    )
    if not datasets_raw:
        # Fallback: try bq command
        result = subprocess.run(
            ["bq", "ls", "--format=json", f"--project_id={project_id}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning("Could not list datasets; will create agent without tables")
            return []
        import json

        try:
            ds_list = json.loads(result.stdout)
            datasets = [d["datasetReference"]["datasetId"] for d in ds_list]
        except Exception:
            return []
    else:
        datasets = [d.strip() for d in datasets_raw.splitlines() if d.strip()]

    tables: list[dict[str, str]] = []
    for ds in datasets[:10]:
        result = subprocess.run(
            ["bq", "ls", "--format=json", f"{project_id}:{ds}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            continue
        import json

        try:
            tbl_list = json.loads(result.stdout)
            for t in tbl_list:
                tid = t.get("tableReference", {}).get("tableId", "")
                if tid in ("_AllSpans", "_AllLogs"):
                    tables.append(
                        {
                            "project_id": project_id,
                            "dataset_id": ds,
                            "table_id": tid,
                        }
                    )
        except Exception:
            continue

    return tables


def create_ca_agent(
    project_id: str,
    agent_id: str,
    location: str,
    tables: list[dict[str, str]],
) -> None:
    """Create the CA Data Agent via the Python SDK."""
    try:
        from google.cloud import geminidataanalytics  # type: ignore[attr-defined]
    except ImportError:
        logger.error(
            "google-cloud-geminidataanalytics not installed.\n"
            "  pip install google-cloud-geminidataanalytics"
        )
        sys.exit(1)

    parent = f"projects/{project_id}/locations/{location}"
    agent_name = f"{parent}/dataAgents/{agent_id}"

    # Check if agent already exists
    agent_client = geminidataanalytics.DataAgentServiceClient()
    try:
        existing = agent_client.get_data_agent(
            request=geminidataanalytics.GetDataAgentRequest(name=agent_name)
        )
        logger.info(f"Agent already exists: {existing.name}")
        logger.info("To recreate, delete it first via the Cloud Console.")
        return
    except Exception:
        pass  # Agent doesn't exist, create it

    # Build BQ table references
    bq_refs = []
    for t in tables:
        ref = geminidataanalytics.BigQueryTableReference()
        ref.project_id = t["project_id"]
        ref.dataset_id = t["dataset_id"]
        ref.table_id = t["table_id"]

        # Add schema descriptions for better query generation
        ref.schema = geminidataanalytics.Schema()
        if t["table_id"] == "_AllSpans":
            ref.schema.description = (
                "Cloud Trace spans exported to BigQuery. Contains distributed "
                "trace data with span_name, service_name, duration, status_code, "
                "parent_span_id, trace_id, and span attributes."
            )
        elif t["table_id"] == "_AllLogs":
            ref.schema.description = (
                "Cloud Logging entries exported to BigQuery. Contains "
                "application and infrastructure logs with severity, "
                "json_payload, text_payload, timestamp, resource labels."
            )
        bq_refs.append(ref)

    # Build datasource references
    ds_refs = geminidataanalytics.DatasourceReferences()
    if bq_refs:
        ds_refs.bq.table_references = bq_refs

    # Build context
    published_ctx = geminidataanalytics.Context()
    published_ctx.system_instruction = SYSTEM_INSTRUCTION
    published_ctx.datasource_references = ds_refs

    # Build agent
    data_agent = geminidataanalytics.DataAgent()
    data_agent.data_analytics_agent.published_context = published_ctx
    data_agent.name = agent_name

    request = geminidataanalytics.CreateDataAgentRequest(
        parent=parent,
        data_agent_id=agent_id,
        data_agent=data_agent,
    )

    try:
        response = agent_client.create_data_agent_sync(request=request)
        logger.info(f"CA Data Agent created: {response.name}")
    except Exception as e:
        logger.error(f"Failed to create CA agent: {e}")
        sys.exit(1)


def grant_ca_permissions(project_id: str, service_account: str | None = None) -> None:
    """Grant IAM roles required for the CA Data Agent."""
    if not service_account:
        project_number = run_gcloud(
            ["projects", "describe", project_id, "--format=value(projectNumber)"],
            exit_on_fail=False,
        )
        if not project_number:
            logger.warning("Could not determine project number; skipping IAM grants")
            return
        service_account = f"{project_number}-compute@developer.gserviceaccount.com"

    roles = [
        "roles/geminidataanalytics.dataAgentCreator",
        "roles/geminidataanalytics.dataAgentUser",
        "roles/bigquery.dataViewer",
        "roles/bigquery.jobUser",
    ]

    logger.info(f"Granting CA IAM roles to {service_account}...")
    for role in roles:
        run_gcloud(
            [
                "projects",
                "add-iam-policy-binding",
                project_id,
                f"--member=serviceAccount:{service_account}",
                f"--role={role}",
                "--condition=None",
            ],
            exit_on_fail=False,
        )
    logger.info("IAM roles granted.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision a Conversational Analytics Data Agent for Auto SRE"
    )
    parser.add_argument("--project-id", required=True, help="GCP project ID")
    parser.add_argument(
        "--agent-id", default=DEFAULT_AGENT_ID, help="CA agent ID (default: ca-autosre)"
    )
    parser.add_argument(
        "--location", default=DEFAULT_LOCATION, help="Location (default: global)"
    )
    parser.add_argument(
        "--service-account", help="Service account email for IAM grants"
    )
    parser.add_argument(
        "--skip-iam", action="store_true", help="Skip IAM permission grants"
    )
    args = parser.parse_args()

    logger.info(f"Setting up CA Data Agent for project: {args.project_id}")

    # 1. Discover BQ tables
    tables = discover_bq_tables(args.project_id)
    if tables:
        logger.info(f"Found {len(tables)} telemetry tables:")
        for t in tables:
            logger.info(f"  {t['project_id']}.{t['dataset_id']}.{t['table_id']}")
    else:
        logger.warning(
            "No _AllSpans or _AllLogs tables found. "
            "Agent will be created without table references. "
            "Configure tables later via Cloud Console."
        )

    # 2. Create the agent
    create_ca_agent(args.project_id, args.agent_id, args.location, tables)

    # 3. Grant IAM permissions
    if not args.skip_iam:
        grant_ca_permissions(args.project_id, args.service_account)

    logger.info("\nSetup complete!")
    logger.info(f"Set environment variable: SRE_AGENT_CA_DATA_AGENT={args.agent_id}")


if __name__ == "__main__":
    main()
