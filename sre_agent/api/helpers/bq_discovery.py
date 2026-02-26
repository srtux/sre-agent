import logging

import httpx
from google.auth import default
from google.auth.transport.requests import Request

from sre_agent.api.helpers.cache import async_ttl_cache
from sre_agent.auth import GLOBAL_CONTEXT_CREDENTIALS

logger = logging.getLogger(__name__)


@async_ttl_cache(ttl_seconds=3600)
async def get_linked_log_dataset(project_id: str) -> str | None:
    """Fetch the BigQuery dataset linked to the Cloud Logging '_Default' bucket.

    Returns the dataset ID (e.g., 'logs') or None if not linked.
    """
    try:
        token = GLOBAL_CONTEXT_CREDENTIALS.token
        if not token:
            credentials, _ = default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(Request())  # type: ignore
            token = credentials.token
    except Exception as exc:
        logger.warning(f"Failed to get GCP credentials for log discovery: {exc}")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": project_id,
    }

    async with httpx.AsyncClient() as client:
        url = f"https://logging.googleapis.com/v2/projects/{project_id}/locations/global/buckets/_Default/links"
        try:
            resp = await client.get(url, headers=headers, timeout=5.0)
            if resp.status_code == 200:
                links = resp.json().get("links", [])
                for link in links:
                    if "bigqueryDataset" in link:
                        dataset_uri = link["bigqueryDataset"].get("datasetId", "")
                        if dataset_uri:
                            return str(dataset_uri.split("/")[-1])
        except Exception as exc:
            logger.debug(f"Logging discovery failed for {project_id}: {exc}")

    return None


@async_ttl_cache(ttl_seconds=3600)
async def get_linked_trace_dataset(project_id: str) -> str | None:
    """Fetch the BigQuery dataset linked to traces (spans).

    Tries multiple strategies:
    1. Scan all buckets via Cloud Logging for links named 'trace' or 'span'.
    2. Scan all buckets via Cloud Observability for links in the 'Spans' dataset path.
    3. Fallback: Check if a dataset literally named 'traces' exists in BigQuery.
    """
    try:
        token = GLOBAL_CONTEXT_CREDENTIALS.token
        if not token:
            credentials, _ = default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(Request())  # type: ignore
            token = credentials.token
    except Exception as exc:
        logger.warning(f"Failed to get GCP credentials for trace discovery: {exc}")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": project_id,
    }

    async with httpx.AsyncClient() as client:
        # Strategy 1: Scan all buckets via Logging API for trace-sounding links
        try:
            buckets_url = f"https://logging.googleapis.com/v2/projects/{project_id}/locations/-/buckets"
            resp = await client.get(buckets_url, headers=headers, timeout=5.0)
            if resp.status_code == 200:
                buckets = resp.json().get("buckets", [])
                for b in buckets:
                    bname = b["name"]
                    links_url = f"https://logging.googleapis.com/v2/{bname}/links"
                    lresp = await client.get(links_url, headers=headers, timeout=5.0)
                    if lresp.status_code == 200:
                        links = lresp.json().get("links", [])
                        for link in links:
                            # If the link name or dataset ID suggests traces/spans, use it
                            link_id = link["name"].split("/")[-1].lower()
                            ds_uri = (
                                link.get("bigqueryDataset", {})
                                .get("datasetId", "")
                                .lower()
                            )
                            if (
                                "trace" in link_id
                                or "span" in link_id
                                or "trace" in ds_uri
                                or "span" in ds_uri
                            ):
                                return str(ds_uri.split("/")[-1])
        except Exception as exc:
            logger.debug(f"Logging-based trace scan failed: {exc}")

        # Strategy 2: Exhaustive scan via Cloud Observability (Checking Spans path)
        try:
            # We already listed buckets above, reuse their names if possible or just try common ones
            obs_locations = ["global", "us"]
            for loc in obs_locations:
                obs_url = f"https://observability.googleapis.com/v1/projects/{project_id}/locations/{loc}/buckets"
                resp = await client.get(obs_url, headers=headers, timeout=5.0)
                if resp.status_code == 200:
                    buckets = resp.json().get("buckets", [])
                    for b in buckets:
                        name = b["name"]  # projects/P/locations/L/buckets/B
                        links_url = f"https://observability.googleapis.com/v1/{name}/datasets/Spans/links"
                        oresp = await client.get(
                            links_url, headers=headers, timeout=5.0
                        )
                        if oresp.status_code == 200:
                            links = oresp.json().get("links", [])
                            for link in links:
                                ds_uri = link.get("bigqueryDataset", {}).get(
                                    "datasetId", ""
                                )
                                if ds_uri:
                                    return str(ds_uri.split("/")[-1])
        except Exception as exc:
            logger.debug(f"Observability-based trace scan failed: {exc}")

    # Strategy 3: Hardcoded fallback check for 'traces' dataset
    # This is a safety net if API discovery is incomplete/slow.
    try:
        from google.cloud import bigquery
        from google.cloud.exceptions import NotFound

        bq_client = bigquery.Client(
            project=project_id, credentials=GLOBAL_CONTEXT_CREDENTIALS
        )
        # Check for 'traces' or 'obs_bucket_spans'
        for candidate in ["traces", "obs_bucket_spans"]:
            try:
                # Check for existence of the _AllSpans table
                table_ref = f"{project_id}.{candidate}._AllSpans"
                bq_client.get_table(table_ref)
                logger.info(f"Auto-discovered trace dataset via fallback: {candidate}")
                return candidate
            except (NotFound, Exception):
                continue
    except Exception as exc:
        logger.debug(f"BigQuery-based fallback check failed: {exc}")

    return None
