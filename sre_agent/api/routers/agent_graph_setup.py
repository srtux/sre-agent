import logging
import re
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from google.api_core.exceptions import Forbidden, NotFound
from google.cloud import bigquery
from pydantic import BaseModel, ConfigDict

from sre_agent.auth import GLOBAL_CONTEXT_CREDENTIALS, is_guest_mode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/graph/setup",
    tags=["Agent Graph Setup"],
)


def _validate_identifier(identifier: str | None, name: str) -> str:
    """Validate that an identifier matches ^[a-zA-Z0-9_.-]+$ or is empty."""
    if not identifier:
        raise HTTPException(status_code=400, detail=f"Invalid {name}: cannot be empty.")
    if not re.match(r"^[a-zA-Z0-9_./-]+$", identifier):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {name}: must match ^[a-zA-Z0-9_./-]+$",
        )
    return identifier


def _get_bq_client(project_id: str) -> bigquery.Client:
    """Return a BigQuery client for the given project, using EUC if available."""
    return bigquery.Client(project=project_id, credentials=GLOBAL_CONTEXT_CREDENTIALS)


def _get_auth_token() -> str:
    """Get a GCP auth token from the current user credentials."""
    token = GLOBAL_CONTEXT_CREDENTIALS.token
    if not token:
        # Fallback to ADC if no user token is in context (e.g. background setup)
        try:
            from google.auth import default
            from google.auth.transport.requests import Request

            credentials, _ = default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(Request())  # type: ignore
            token = credentials.token
        except Exception as exc:
            logger.warning(f"Failed to get fallback ADC token: {exc}")
            token = None

    if not token:
        raise HTTPException(
            status_code=401, detail="Failed to obtain Google Cloud access token."
        )
    return token


@router.get("/check_bucket")
async def check_observability_bucket(project_id: str) -> dict[str, Any]:
    """Check if an Observability bucket exists for the project."""
    if is_guest_mode():
        return {"exists": True, "buckets": [{"name": "demo-bucket"}]}
    _validate_identifier(project_id, "project_id")
    token = _get_auth_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project_id,
    }

    url = f"https://observability.googleapis.com/v1/projects/{project_id}/locations/us/buckets"

    # We use httpx rather than google-api-core as the management plane client isn't fully published
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied to list Observability Buckets. Require roles/observability.admin or equivalent.",
                )
            resp.raise_for_status()
            data = resp.json()

            buckets = data.get("buckets", [])
            # Search for the default trace bucket name, usually traces, but we can just see if there are any buckets
            has_bucket = len(buckets) > 0

            return {"exists": has_bucket, "buckets": buckets}
        except httpx.HTTPStatusError as exc:
            logger.exception("Failed to check Observability Bucket.")
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Failed to check Observability Bucket: {exc.response.text}",
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error checking Observability Bucket.")
            raise HTTPException(
                status_code=500,
                detail="Unexpected error checking Observability Bucket.",
            ) from exc


class LinkDatasetRequest(BaseModel):
    """Request schema for linking an Observability bucket to a BigQuery dataset."""

    model_config = ConfigDict(extra="forbid")
    project_id: str
    bucket_id: str
    dataset_id: str = "traces"


@router.post("/link_dataset")
async def link_dataset(req: LinkDatasetRequest) -> dict[str, Any]:
    """Create a BigQuery dataset and link it to the Observability bucket."""
    if is_guest_mode():
        return {"status": "already_linked", "link": {}, "link_id": "demo"}
    _validate_identifier(req.project_id, "project_id")
    _validate_identifier(req.bucket_id, "bucket_id")
    _validate_identifier(req.dataset_id, "dataset_id")

    # 1. Create the BigQuery dataset if it doesn't exist
    client = _get_bq_client(req.project_id)
    dataset_ref = f"{req.project_id}.{req.dataset_id}"
    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset {dataset_ref} already exists.")
    except NotFound:
        logger.info(f"Creating dataset {dataset_ref}...")
        try:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            client.create_dataset(dataset, timeout=30)
        except Forbidden as exc:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied to create BigQuery dataset '{req.dataset_id}'. Require roles/bigquery.dataEditor or roles/bigquery.admin.",
            ) from exc

    # 2. Check existing links
    token = _get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": req.project_id,
    }

    base_url = f"https://observability.googleapis.com/v1/projects/{req.project_id}/locations/us/buckets/{req.bucket_id}/datasets/Spans"

    async with httpx.AsyncClient() as http_client:
        # Check if already linked
        try:
            resp = await http_client.get(
                f"{base_url}/links", headers=headers, timeout=10.0
            )
            resp.raise_for_status()
            links = resp.json().get("links", [])
            for link in links:
                if link.get("name"):
                    link_id = link["name"].split("/")[-1]
                    return {
                        "status": "already_linked",
                        "link": link,
                        "link_id": link_id,
                    }
        except Exception as exc:
            logger.warning(f"Failed to list links, proceeding to create: {exc}")

        # 3. Create the link
        try:
            link_id = re.sub(r"[^a-zA-Z0-9_]", "_", req.dataset_id)
            resp = await http_client.post(
                f"{base_url}/links?linkId={link_id}",
                headers=headers,
                json={},
                timeout=10.0,
            )
            resp.raise_for_status()
            return {"status": "creating", "operation": resp.json()}
        except httpx.HTTPStatusError as exc:
            logger.exception("Failed to create observability link.")
            detail_msg = exc.response.text
            if exc.response.status_code == 403:
                detail_msg = "Permission denied to create Observability Link. Require roles/observability.admin."
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=detail_msg,
            ) from exc


@router.get("/lro_status")
async def get_lro_status(project_id: str, operation_name: str) -> dict[str, Any]:
    """Poll the status of a Long Running Operation."""
    if is_guest_mode():
        return {"done": True}
    _validate_identifier(project_id, "project_id")
    if (
        not operation_name.startswith("projects/")
        or "/operations/" not in operation_name
    ):
        raise HTTPException(status_code=400, detail="Invalid operation name format.")

    token = _get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project_id,
    }

    url = f"https://observability.googleapis.com/v1/{operation_name}"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=10.0)
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result
        except httpx.HTTPStatusError as exc:
            logger.exception(f"Failed to get LRO status for {operation_name}")
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Failed to get LRO status: {exc.response.text}",
            ) from exc


@router.get("/verify")
async def verify_dataset(project_id: str, dataset_id: str = "traces") -> dict[str, Any]:
    """Verify that the dataset and _AllSpans view are accessible."""
    if is_guest_mode():
        return {
            "verified": True,
            "dataset": "demo",
            "view": "demo._AllSpans",
            "type": "VIEW",
        }
    _validate_identifier(project_id, "project_id")
    _validate_identifier(dataset_id, "dataset_id")

    client = _get_bq_client(project_id)
    try:
        # Check dataset
        dataset_ref = f"{project_id}.{dataset_id}"
        client.get_dataset(dataset_ref)

        # Check _AllSpans view
        view_ref = f"{project_id}.{dataset_id}._AllSpans"
        table = client.get_table(view_ref)

        return {
            "verified": True,
            "dataset": dataset_ref,
            "view": view_ref,
            "type": table.table_type,
        }
    except Forbidden as exc:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied to read BigQuery dataset '{dataset_id}'. Require roles/bigquery.dataViewer.",
        ) from exc
    except NotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_id}' or view '_AllSpans' not found. It may still be provisioning.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error verifying dataset: {exc!s}"
        ) from exc


class SchemaStepRequest(BaseModel):
    """Request schema for executing a single step in the Agent Graph BigQuery schema generation."""

    model_config = ConfigDict(extra="forbid")
    project_id: str
    trace_dataset: str = "traces"
    graph_dataset: str = "agentops"


@router.post("/schema/{step}")
async def execute_schema_step(step: str, req: SchemaStepRequest) -> dict[str, Any]:
    """Execute a specific BigQuery schema setup step."""
    if is_guest_mode():
        return {"status": "success", "message": f"Step {step} completed (demo mode)."}
    _validate_identifier(req.project_id, "project_id")
    _validate_identifier(req.trace_dataset, "trace_dataset")
    _validate_identifier(req.graph_dataset, "graph_dataset")

    valid_steps = [
        "create_dataset",
        "cleanup",
        "agent_spans_raw",
        "nodes",
        "edges",
        "trajectories",
        "graph",
        "hourly",
        "backfill",
        "registries",
        "scheduled_query",
    ]
    if step not in valid_steps:
        raise HTTPException(status_code=400, detail=f"Invalid schema step: {step}")

    client = _get_bq_client(req.project_id)

    pd = req.project_id
    gd = req.graph_dataset
    td = req.trace_dataset

    def run_query(sql: str) -> None:
        try:
            client.query_and_wait(sql)
        except Forbidden as exc:
            # Parse BigQuery permission errors
            roles = "roles/bigquery.admin or roles/bigquery.dataEditor"
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied to execute BigQuery DDL. Require {roles}.",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"BigQuery execution failed: {exc!s}"
            ) from exc

    try:
        if step == "create_dataset":
            try:
                client.get_dataset(f"{pd}.{gd}")
                return {"status": "success", "message": f"Dataset {gd} already exists."}
            except NotFound:
                dataset = bigquery.Dataset(f"{pd}.{gd}")
                dataset.location = "US"
                try:
                    client.create_dataset(dataset, timeout=30)
                except Forbidden as exc:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied to create BigQuery dataset '{gd}'. Require roles/bigquery.dataEditor.",
                    ) from exc
                return {"status": "success", "message": f"Created dataset {gd}."}

        elif step == "cleanup":
            run_query(f"DROP PROPERTY GRAPH IF EXISTS `{pd}.{gd}.agent_topology_graph`")
            run_query(f"DROP PROPERTY GRAPH IF EXISTS `{pd}.{gd}.agent_trace_graph`")

            for v in [
                "agent_topology_edges",
                "agent_topology_nodes",
                "agent_trajectories",
                "agent_span_payloads",
            ]:
                client.delete_table(f"{pd}.{gd}.{v}", not_found_ok=True)

            run_query(f"DROP MATERIALIZED VIEW IF EXISTS `{pd}.{gd}.agent_spans_raw`")
            client.delete_table(f"{pd}.{gd}.agent_spans_raw", not_found_ok=True)
            return {"status": "success", "message": "Cleanup complete."}

        elif step == "agent_spans_raw":
            sql = f"""
            CREATE MATERIALIZED VIEW `{pd}.{gd}.agent_spans_raw`
            PARTITION BY DATE(start_time)
            CLUSTER BY trace_id, session_id, node_label
            OPTIONS (
              enable_refresh = true, refresh_interval_minutes = 5,
              max_staleness = INTERVAL "30" MINUTE, allow_non_incremental_definition = true
            ) AS
            SELECT
              span_id, parent_span_id AS parent_id, trace_id, start_time,
              JSON_VALUE(attributes, '$."gen_ai.conversation.id"') AS session_id,
              JSON_VALUE(attributes, '$."user.id"') AS user_id,
              CAST(duration_nano AS FLOAT64) / 1000000.0 AS duration_ms,
              CASE status.code WHEN 0 THEN 'UNSET' WHEN 1 THEN 'OK' WHEN 2 THEN 'ERROR' ELSE CAST(status.code AS STRING) END AS status_code,
              status.message AS status_desc,
              SAFE_CAST(JSON_VALUE(attributes, '$."gen_ai.usage.input_tokens"') AS INT64) AS input_tokens,
              SAFE_CAST(JSON_VALUE(attributes, '$."gen_ai.usage.output_tokens"') AS INT64) AS output_tokens,
              JSON_VALUE(attributes, '$."gen_ai.tool.type"') AS tool_type,
              JSON_VALUE(attributes, '$."gen_ai.request.model"') AS request_model,
              JSON_VALUE(attributes, '$."gen_ai.response.finish_reasons"') AS finish_reasons,
              JSON_VALUE(attributes, '$."gen_ai.system"') AS system,
              JSON_VALUE(attributes, '$."gen_ai.agent.id"') AS agent_id,
              JSON_VALUE(attributes, '$."gen_ai.agent.version"') AS agent_version,
              JSON_VALUE(attributes, '$."gen_ai.tool.id"') AS tool_id,
              JSON_VALUE(attributes, '$."gen_ai.system_instructions"') AS system_instructions,
              JSON_VALUE(attributes, '$."gen_ai.data_source.id"') AS data_source_id,
              JSON_VALUE(attributes, '$."gen_ai.output.type"') AS output_type,
              SAFE_CAST(JSON_VALUE(attributes, '$."gen_ai.request.temperature"') AS FLOAT64) AS request_temperature,
              SAFE_CAST(JSON_VALUE(attributes, '$."gen_ai.request.top_p"') AS FLOAT64) AS request_top_p,
              COALESCE(JSON_VALUE(attributes, '$."gen_ai.agent.description"'), JSON_VALUE(attributes, '$."gen_ai.tool.description"')) AS node_description,
              CASE WHEN JSON_VALUE(attributes, '$."gen_ai.operation.name"') = 'invoke_agent' THEN 'Agent' WHEN JSON_VALUE(attributes, '$."gen_ai.operation.name"') = 'execute_tool' THEN 'Tool' WHEN JSON_VALUE(attributes, '$."gen_ai.operation.name"') = 'generate_content' THEN 'LLM' ELSE 'Glue' END AS node_type,
              COALESCE(JSON_VALUE(attributes, '$."gen_ai.agent.name"'), JSON_VALUE(attributes, '$."gen_ai.tool.name"'), JSON_VALUE(attributes, '$."gen_ai.response.model"'), name) AS node_label,
              JSON_VALUE(resource.attributes, '$.\"service.name\"') AS service_name,
              JSON_VALUE(resource.attributes, '$.\"cloud.resource_id\"') AS resource_id,
              CONCAT(
                CASE
                  WHEN JSON_VALUE(attributes, '$."gen_ai.operation.name"') = 'invoke_agent' THEN 'Agent'
                  WHEN JSON_VALUE(attributes, '$."gen_ai.operation.name"') = 'execute_tool' THEN 'Tool'
                  WHEN JSON_VALUE(attributes, '$."gen_ai.operation.name"') = 'generate_content' THEN 'LLM'
                  ELSE 'Glue'
                END,
                '::',
                COALESCE(JSON_VALUE(attributes, '$."gen_ai.agent.name"'), JSON_VALUE(attributes, '$."gen_ai.tool.name"'), JSON_VALUE(attributes, '$."gen_ai.response.model"'), name)
              ) AS logical_node_id
            FROM `{pd}.{td}._AllSpans`
            WHERE JSON_VALUE(resource.attributes, '$."cloud.platform"') = 'gcp.agent_engine';
            """
            run_query(sql)
            return {"status": "success", "message": "Created agent_spans_raw."}

        elif step == "nodes":
            sql = f"""
            CREATE OR REPLACE VIEW `{pd}.{gd}.agent_topology_nodes` AS
            SELECT trace_id, session_id, logical_node_id, ANY_VALUE(service_name) AS service_name,
              ANY_VALUE(node_type) AS node_type, ANY_VALUE(node_label) AS node_label, ANY_VALUE(node_description) AS node_description,
              COUNT(span_id) AS execution_count, SUM(duration_ms) AS total_duration_ms,
              SUM(input_tokens) AS total_input_tokens, SUM(output_tokens) AS total_output_tokens,
              COUNTIF(status_code = 'ERROR') AS error_count, MIN(start_time) AS start_time
            FROM `{pd}.{gd}.agent_spans_raw` WHERE node_type != 'Glue' GROUP BY 1, 2, 3
            UNION ALL
            SELECT trace_id, session_id, 'User::session' AS logical_node_id, ANY_VALUE(service_name) AS service_name,
              'User' AS node_type, 'session' AS node_label, 'End user session entry point' AS node_description, APPROX_COUNT_DISTINCT(span_id) AS execution_count,
              SUM(duration_ms) AS total_duration_ms, SUM(input_tokens) AS total_input_tokens,
              SUM(output_tokens) AS total_output_tokens, COUNTIF(status_code = 'ERROR') AS error_count, MIN(start_time) AS start_time
            FROM `{pd}.{gd}.agent_spans_raw` WHERE node_type = 'Agent'
              AND (parent_id IS NULL OR parent_id NOT IN (SELECT span_id FROM `{pd}.{gd}.agent_spans_raw` WHERE node_type != 'Glue'))
            GROUP BY 1, 2;
            """
            run_query(sql)
            return {"status": "success", "message": "Created agent_topology_nodes."}

        elif step == "edges":
            sql = f"""
            CREATE OR REPLACE VIEW `{pd}.{gd}.agent_topology_edges` AS
              WITH RECURSIVE span_tree AS (
              SELECT span_id, trace_id, session_id, node_type, logical_node_id, CAST(NULL AS STRING) AS ancestor_logical_id,
                service_name, duration_ms, input_tokens, output_tokens, status_code, start_time, system
              FROM `{pd}.{gd}.agent_spans_raw`
              WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
                AND (parent_id IS NULL OR parent_id NOT IN (SELECT span_id FROM `{pd}.{gd}.agent_spans_raw` WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)))
              UNION ALL
              SELECT child.span_id, child.trace_id, child.session_id, child.node_type, child.logical_node_id,
                IF(parent.node_type != 'Glue', parent.logical_node_id, parent.ancestor_logical_id),
                child.service_name, child.duration_ms, child.input_tokens, child.output_tokens, child.status_code, child.start_time, child.system
              FROM `{pd}.{gd}.agent_spans_raw` child
              JOIN span_tree parent ON child.parent_id = parent.span_id
              WHERE child.start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            )
            SELECT trace_id, session_id, ANY_VALUE(service_name) AS service_name,
              ancestor_logical_id AS source_node_id, logical_node_id AS destination_node_id, COUNT(*) as edge_weight,
              SUM(duration_ms) as total_duration_ms, SUM(IFNULL(input_tokens, 0) + IFNULL(output_tokens, 0)) as total_tokens,
              SUM(IFNULL(input_tokens, 0)) as input_tokens, SUM(IFNULL(output_tokens, 0)) as output_tokens,
              COUNTIF(status_code = 'ERROR') as error_count, MIN(start_time) as start_time
            FROM span_tree WHERE node_type != 'Glue' AND ancestor_logical_id IS NOT NULL AND ancestor_logical_id != logical_node_id GROUP BY 1, 2, 4, 5
            UNION ALL
            SELECT trace_id, session_id, ANY_VALUE(service_name) AS service_name, 'User::session' AS source_node_id,
              logical_node_id AS destination_node_id, COUNT(*) as edge_weight, SUM(duration_ms) as total_duration_ms,
              SUM(IFNULL(input_tokens, 0) + IFNULL(output_tokens, 0)) as total_tokens, SUM(IFNULL(input_tokens, 0)) as input_tokens,
              SUM(IFNULL(output_tokens, 0)) as output_tokens, COUNTIF(status_code = 'ERROR') as error_count, MIN(start_time) as start_time
            FROM span_tree WHERE node_type = 'Agent' AND ancestor_logical_id IS NULL GROUP BY 1, 2, 4, 5;
            """
            run_query(sql)
            return {"status": "success", "message": "Created agent_topology_edges."}

        elif step == "trajectories":
            client.delete_table(f"{pd}.{gd}.agent_trajectories", not_found_ok=True)
            sql = f"""
            CREATE OR REPLACE VIEW `{pd}.{gd}.agent_trajectories` AS
            WITH sequenced_steps AS (
              SELECT trace_id, session_id, service_name, span_id, node_type, node_label, logical_node_id, start_time, duration_ms, status_code, input_tokens, output_tokens,
                ROW_NUMBER() OVER(PARTITION BY trace_id ORDER BY start_time ASC) AS step_sequence
              FROM `{pd}.{gd}.agent_spans_raw` WHERE node_type != 'Glue'
            ),
            trajectory_links AS (
              SELECT a.trace_id, a.session_id, a.service_name, a.logical_node_id AS source_node, a.node_type AS source_type, a.node_label AS source_label,
                b.logical_node_id AS target_node, b.node_type AS target_type, b.node_label AS target_label, a.step_sequence AS source_step, b.step_sequence AS target_step,
                a.duration_ms AS source_duration_ms, b.duration_ms AS target_duration_ms, a.status_code AS source_status, b.status_code AS target_status,
                COALESCE(a.input_tokens, 0) + COALESCE(a.output_tokens, 0) AS source_tokens, COALESCE(b.input_tokens, 0) + COALESCE(b.output_tokens, 0) AS target_tokens
              FROM sequenced_steps a JOIN sequenced_steps b ON a.trace_id = b.trace_id AND a.step_sequence + 1 = b.step_sequence
            )
            SELECT ANY_VALUE(service_name) AS service_name, source_node, source_type, source_label, target_node, target_type, target_label,
              APPROX_COUNT_DISTINCT(trace_id) AS trace_count, SUM(source_duration_ms) AS total_source_duration_ms, SUM(target_duration_ms) AS total_target_duration_ms,
              SUM(source_tokens) AS total_source_tokens, SUM(target_tokens) AS total_target_tokens, COUNTIF(source_status = 'ERROR' OR target_status = 'ERROR') AS error_transition_count
            FROM trajectory_links GROUP BY 2, 3, 4, 5, 6, 7;
            """
            run_query(sql)
            return {"status": "success", "message": "Created agent_trajectories."}

        elif step == "graph":
            sql = f"""
            CREATE OR REPLACE PROPERTY GRAPH `{pd}.{gd}.agent_topology_graph`
              NODE TABLES (`{pd}.{gd}.agent_topology_nodes` AS Node KEY (trace_id, logical_node_id) LABEL Component PROPERTIES ALL COLUMNS)
              EDGE TABLES (`{pd}.{gd}.agent_topology_edges` AS Interaction KEY (trace_id, source_node_id, destination_node_id)
                SOURCE KEY (trace_id, source_node_id) REFERENCES Node (trace_id, logical_node_id)
                DESTINATION KEY (trace_id, destination_node_id) REFERENCES Node (trace_id, logical_node_id)
                LABEL Interaction PROPERTIES ALL COLUMNS);
            """
            run_query(sql)
            return {"status": "success", "message": "Created agent_topology_graph."}

        elif step == "hourly":
            client.delete_table(f"{pd}.{gd}.agent_graph_hourly", not_found_ok=True)
            sql = f"""
            CREATE TABLE `{pd}.{gd}.agent_graph_hourly` (
              time_bucket TIMESTAMP NOT NULL, source_id STRING, target_id STRING, source_type STRING, target_type STRING,
              call_count INT64, error_count INT64, edge_tokens INT64, input_tokens INT64, output_tokens INT64, total_cost FLOAT64,
              sum_duration_ms FLOAT64, max_p95_duration_ms FLOAT64, unique_sessions INT64, sample_error STRING,
              node_total_tokens INT64, node_input_tokens INT64, node_output_tokens INT64, node_has_error BOOL,
              node_sum_duration_ms FLOAT64, node_max_p95_duration_ms FLOAT64, node_error_count INT64, node_call_count INT64,
              node_total_cost FLOAT64, node_description STRING, tool_call_count INT64, llm_call_count INT64,
              downstream_total_tokens INT64, downstream_total_cost FLOAT64, downstream_tool_call_count INT64, downstream_llm_call_count INT64,
              session_ids ARRAY<STRING>, service_name STRING
            ) PARTITION BY DATE(time_bucket) CLUSTER BY service_name, source_id, target_id OPTIONS (description = 'Pre-aggregated hourly agent graph data');
            """
            run_query(sql)
            return {"status": "success", "message": "Created agent_graph_hourly."}

        elif step == "backfill":
            sql = f"""
            INSERT INTO `{pd}.{gd}.agent_graph_hourly`
            WITH RawEdges AS (
              SELECT e.trace_id, e.session_id, TIMESTAMP_TRUNC(n_dst.start_time, HOUR) as time_bucket, e.source_node_id as source_id, n_src.node_type as source_type,
                e.destination_node_id as target_id, n_dst.node_type as target_type, e.edge_weight as call_count, e.total_duration_ms, e.total_tokens,
                e.error_count as edge_error_count, n_dst.total_input_tokens as input_tokens, n_dst.total_output_tokens as output_tokens, n_dst.service_name, n_dst.start_time,
                n_dst.node_description
              FROM `{pd}.{gd}.agent_topology_edges` e
              JOIN `{pd}.{gd}.agent_topology_nodes` n_dst ON e.trace_id = n_dst.trace_id AND e.destination_node_id = n_dst.logical_node_id
              LEFT JOIN `{pd}.{gd}.agent_topology_nodes` n_src ON e.trace_id = n_src.trace_id AND e.source_node_id = n_src.logical_node_id
              WHERE n_dst.start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 720 HOUR)
            ),
            CostPaths AS (
              SELECT re.*, COALESCE(input_tokens, 0) * CASE WHEN target_id LIKE '%flash%' THEN 0.00000015 WHEN target_id LIKE '%2.5-pro%' THEN 0.00000125 WHEN target_id LIKE '%1.5-pro%' THEN 0.00000125 ELSE 0.0000005 END + COALESCE(output_tokens, 0) * CASE WHEN target_id LIKE '%flash%' THEN 0.0000006 WHEN target_id LIKE '%2.5-pro%' THEN 0.00001 WHEN target_id LIKE '%1.5-pro%' THEN 0.000005 ELSE 0.000002 END AS span_cost
              FROM RawEdges re
            )
            SELECT time_bucket, source_id, target_id, source_type, target_type, SUM(call_count) AS call_count, SUM(edge_error_count) AS error_count, SUM(total_tokens) AS edge_tokens, SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens, ROUND(SUM(span_cost), 6) AS total_cost, SUM(total_duration_ms) AS sum_duration_ms, ROUND(MAX(total_duration_ms), 2) AS max_p95_duration_ms, APPROX_COUNT_DISTINCT(session_id) AS unique_sessions, CAST(NULL AS STRING) AS sample_error, SUM(total_tokens) AS node_total_tokens, SUM(input_tokens) AS node_input_tokens, SUM(output_tokens) AS node_output_tokens, SUM(edge_error_count) > 0 AS node_has_error, SUM(total_duration_ms) AS node_sum_duration_ms, ROUND(MAX(total_duration_ms), 2) AS node_max_p95_duration_ms, SUM(edge_error_count) AS node_error_count, SUM(call_count) AS node_call_count, ROUND(SUM(span_cost), 6) AS node_total_cost, ANY_VALUE(node_description) AS node_description, SUM(IF(target_type = 'Tool', call_count, 0)) AS tool_call_count, SUM(IF(target_type = 'LLM', call_count, 0)) AS llm_call_count, SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS downstream_total_tokens, ROUND(SUM(span_cost), 6) AS downstream_total_cost, SUM(IF(target_type = 'Tool', call_count, 0)) AS downstream_tool_call_count, SUM(IF(target_type = 'LLM', call_count, 0)) AS downstream_llm_call_count, ARRAY_AGG(DISTINCT session_id IGNORE NULLS) AS session_ids, ANY_VALUE(service_name) AS service_name
            FROM CostPaths GROUP BY time_bucket, source_id, target_id, source_type, target_type;
            """
            run_query(sql)
            return {"status": "success", "message": "Backfilled agent_graph_hourly."}

            sql1 = f"""
            CREATE OR REPLACE VIEW `{pd}.{gd}.agent_registry` AS
            WITH ParsedAgents AS (
              SELECT trace_id, session_id, TIMESTAMP_TRUNC(start_time, HOUR) as time_bucket, service_name, logical_node_id, duration_ms, input_tokens, output_tokens, status_code, node_label, node_type, resource_id, node_description
              FROM `{pd}.{gd}.agent_spans_raw` WHERE node_type = 'Agent'
            )
            SELECT
              time_bucket, service_name, logical_node_id AS agent_id, ANY_VALUE(resource_id) AS engine_id,
              ANY_VALUE(node_label) AS agent_name, ANY_VALUE(node_description) AS description,
              APPROX_COUNT_DISTINCT(session_id) AS total_sessions, COUNT(*) AS total_turns,
              SUM(input_tokens) AS total_input_tokens, SUM(output_tokens) AS total_output_tokens,
              COUNTIF(status_code = 'ERROR') AS error_count,
              APPROX_QUANTILES(duration_ms, 100)[OFFSET(50)] AS p50_duration_ms,
              APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS p95_duration_ms
            FROM ParsedAgents GROUP BY time_bucket, service_name, agent_id;
            """
            run_query(sql1)

            sql2 = f"""
            CREATE OR REPLACE VIEW `{pd}.{gd}.tool_registry` AS
            WITH ParsedTools AS (
              SELECT trace_id, session_id, TIMESTAMP_TRUNC(start_time, HOUR) as time_bucket, service_name, logical_node_id, duration_ms, status_code, node_label, node_description, node_type
              FROM `{pd}.{gd}.agent_spans_raw` WHERE node_type = 'Tool'
            )
            SELECT time_bucket, service_name, logical_node_id AS tool_id, ANY_VALUE(node_label) AS tool_name, ANY_VALUE(node_description) AS description, COUNT(*) AS execution_count, COUNTIF(status_code = 'ERROR') AS error_count, SAFE_DIVIDE(COUNTIF(status_code = 'ERROR'), COUNT(*)) AS error_rate, AVG(duration_ms) AS avg_duration_ms, APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS p95_duration_ms
            FROM ParsedTools GROUP BY time_bucket, service_name, tool_id;
            """
            run_query(sql2)
            return {"status": "success", "message": "Created registries."}

        elif step == "scheduled_query":
            import json
            import subprocess

            # Define the SQL for the scheduled query (incremental hourly update)
            hourly_sql = f"""
            INSERT INTO `{pd}.{gd}.agent_graph_hourly`
            WITH RawEdges AS (
              SELECT e.trace_id, e.session_id, TIMESTAMP_TRUNC(n_dst.start_time, HOUR) as time_bucket, e.source_node_id as source_id, n_src.node_type as source_type,
                e.destination_node_id as target_id, n_dst.node_type as target_type, e.edge_weight as call_count, e.total_duration_ms, e.total_tokens,
                e.error_count as edge_error_count, n_dst.total_input_tokens as input_tokens, n_dst.total_output_tokens as output_tokens, n_dst.service_name, n_dst.start_time,
                n_dst.node_description
              FROM `{pd}.{gd}.agent_topology_edges` e
              JOIN `{pd}.{gd}.agent_topology_nodes` n_dst ON e.trace_id = n_dst.trace_id AND e.destination_node_id = n_dst.logical_node_id
              JOIN `{pd}.{gd}.agent_topology_nodes` n_src ON e.trace_id = n_src.trace_id AND e.source_node_id = n_src.logical_node_id
              WHERE n_dst.start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
                AND n_dst.start_time < TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), HOUR)
            ),
            CostPaths AS (
              SELECT re.*, COALESCE(input_tokens, 0) * CASE WHEN target_id LIKE '%flash%' THEN 0.00000015 WHEN target_id LIKE '%2.5-pro%' THEN 0.00000125 WHEN target_id LIKE '%1.5-pro%' THEN 0.00000125 ELSE 0.0000005 END + COALESCE(output_tokens, 0) * CASE WHEN target_id LIKE '%flash%' THEN 0.0000006 WHEN target_id LIKE '%2.5-pro%' THEN 0.00001 WHEN target_id LIKE '%1.5-pro%' THEN 0.000005 ELSE 0.000002 END AS span_cost
              FROM RawEdges re
            ),
            ExistingBuckets AS (
              SELECT DISTINCT time_bucket FROM `{pd}.{gd}.agent_graph_hourly`
              WHERE time_bucket >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
            ),
            NewPaths AS (
              SELECT cp.* FROM CostPaths cp
              LEFT JOIN ExistingBuckets eb ON cp.time_bucket = eb.time_bucket
              WHERE eb.time_bucket IS NULL
            )
            SELECT time_bucket, source_id, target_id, source_type, target_type, SUM(call_count) AS call_count, SUM(edge_error_count) AS error_count, SUM(total_tokens) AS edge_tokens, SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens, ROUND(SUM(span_cost), 6) AS total_cost, SUM(total_duration_ms) AS sum_duration_ms, ROUND(MAX(total_duration_ms), 2) AS max_p95_duration_ms, COUNT(DISTINCT session_id) AS unique_sessions, CAST(NULL AS STRING) AS sample_error, SUM(total_tokens) AS node_total_tokens, SUM(input_tokens) AS node_input_tokens, SUM(output_tokens) AS node_output_tokens, SUM(edge_error_count) > 0 AS node_has_error, SUM(total_duration_ms) AS node_sum_duration_ms, ROUND(MAX(total_duration_ms), 2) AS node_max_p95_duration_ms, SUM(edge_error_count) AS node_error_count, SUM(call_count) AS node_call_count, ROUND(SUM(span_cost), 6) AS node_total_cost, ANY_VALUE(node_description) AS node_description, SUM(IF(target_type = 'Tool', call_count, 0)) AS tool_call_count, SUM(IF(target_type = 'LLM', call_count, 0)) AS llm_call_count, SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS downstream_total_tokens, ROUND(SUM(span_cost), 6) AS downstream_total_cost, SUM(IF(target_type = 'Tool', call_count, 0)) AS downstream_tool_call_count, SUM(IF(target_type = 'LLM', call_count, 0)) AS downstream_llm_call_count, ARRAY_AGG(DISTINCT session_id IGNORE NULLS) AS session_ids, ANY_VALUE(service_name) AS service_name
            FROM NewPaths GROUP BY time_bucket, source_id, target_id, source_type, target_type;
            """

            config_name = "Agent Graph Hourly Refresh"
            # Check if it already exists using bq ls
            try:
                ls_cmd = [
                    "bq",
                    "ls",
                    "--transfer_config",
                    f"--project_id={pd}",
                    "--transfer_location=US",
                    "--format=json",
                ]
                ls_proc = subprocess.run(
                    ls_cmd, capture_output=True, text=True, check=True
                )
                configs = json.loads(ls_proc.stdout)
                for config in configs:
                    if config.get("displayName") == config_name:
                        return {
                            "status": "success",
                            "message": f"Scheduled query '{config_name}' already exists.",
                        }
            except Exception as e:
                logger.warning(f"Failed to check for existing scheduled query: {e}")

            # Create it
            params = json.dumps({"query": hourly_sql})
            mk_cmd = [
                "bq",
                "mk",
                "--transfer_config",
                f"--project_id={pd}",
                f"--target_dataset={gd}",
                f"--display_name={config_name}",
                "--schedule=every 1 hours",
                "--data_source=scheduled_query",
                f"--params={params}",
            ]
            try:
                subprocess.run(mk_cmd, capture_output=True, text=True, check=True)
                return {
                    "status": "success",
                    "message": f"Created scheduled query: {config_name}",
                }
            except subprocess.CalledProcessError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create scheduled query via bq CLI: {e.stderr}",
                ) from e
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error creating scheduled query: {e!s}",
                ) from e

        return {"status": "error", "message": f"Step {step} not implemented."}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unhandled error in schema step {step}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
