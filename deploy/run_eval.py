#!/usr/bin/env python3
"""Run the SRE Agent evaluation suite.

This script orchestrates agent evaluations using the ADK ``adk eval`` CLI and
optionally syncs results to the Vertex AI GenAI Evaluation Service for
historical tracking in the GCP Console.

Usage::

    # Local evaluation (fast, default)
    python deploy/run_eval.py

    # With Vertex AI cloud sync
    python deploy/run_eval.py --sync

    # Override project ID
    python deploy/run_eval.py --project my-project-id
"""

import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Disable OTEL and standard exporters for the evaluation process itself
# to prevent background threads from hanging or emitting noise.
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_TRACES_EXPORTER"] = "none"
os.environ["OTEL_METRICS_EXPORTER"] = "none"
os.environ["OTEL_LOGS_EXPORTER"] = "none"
os.environ["SRE_AGENT_EVAL_MODE"] = "true"

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Placeholder project IDs used in test data files
_PLACEHOLDER_PROJECT_IDS = [
    "TEST_PROJECT_ID",
    "microservices-prod",
    "search-prod",
    "ecommerce-prod",
    "web-platform-prod",
    "payments-prod",
]


def _parse_args(argv: list[str]) -> tuple[list[str], bool, str | None]:
    """Parse CLI arguments, separating flags from control options.

    Returns:
        Tuple of (passthrough_flags, should_sync_cloud, project_id_override).
    """
    flags: list[str] = []
    should_sync = False
    project_id = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--sync":
            should_sync = True
            i += 1
            continue
        if arg == "--project":
            if i + 1 < len(argv):
                project_id = argv[i + 1]
                i += 2
                continue
        if arg.startswith("-"):
            flags.append(arg)
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                flags.append(argv[i + 1])
                i += 1
        i += 1

    return flags, should_sync, project_id


def _resolve_project_id(project_id_override: str | None) -> str:
    """Resolve the GCP project ID from flag, env, or fallback."""
    project_id = project_id_override or os.environ.get("GOOGLE_CLOUD_PROJECT")

    # Sanitize comma-separated values (Cloud Build quirk)
    if project_id and "," in project_id:
        project_id = project_id.split(",")[0].strip()

    if not project_id:
        print(
            "WARNING: GOOGLE_CLOUD_PROJECT not set. Using 'my-test-project' as fallback."
        )
        project_id = "my-test-project"

    # Propagate to subprocess environment
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GCP_PROJECT_ID"] = project_id
    return project_id


def _substitute_placeholders(content: str, project_id: str) -> str:
    """Replace placeholder project IDs with the actual project ID."""
    for placeholder in _PLACEHOLDER_PROJECT_IDS:
        content = content.replace(placeholder, project_id)
    return content


def _prepare_eval_files(project_id: str, temp_dir: str) -> list[str]:
    """Copy eval files to temp dir with project ID placeholders replaced."""
    original_files = glob.glob("eval/*.test.json")
    processed = []

    for file_path in original_files:
        try:
            with open(file_path) as f:
                content = f.read()

            modified = _substitute_placeholders(content, project_id)
            dest = os.path.join(temp_dir, Path(file_path).name)

            with open(dest, "w") as f:
                f.write(modified)

            processed.append(dest)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            processed.append(file_path)

    return processed


def _run_adk_eval(
    flags: list[str], eval_files: list[str]
) -> subprocess.CompletedProcess:
    """Execute the ADK eval CLI."""
    cmd = ["adk", "eval", *flags]

    config_path = "eval/test_config.json"
    if os.path.exists(config_path):
        cmd.extend(["--config_file_path", config_path])

    cmd.extend(["sre_agent", *eval_files])

    storage_uri = os.environ.get("EVAL_STORAGE_URI")
    if storage_uri:
        cmd.extend(["--eval_storage_uri", storage_uri])

    print(f"Running ADK Eval: {' '.join(cmd)}")
    sys.stdout.flush()

    return subprocess.run(cmd)


def _extract_text_from_parts(parts):
    """Extract text from ADK Content parts structure."""
    if isinstance(parts, str):
        return parts
    if isinstance(parts, list):
        text_parts = []
        for p in parts:
            if isinstance(p, dict) and "text" in p:
                text_parts.append(p["text"])
            elif isinstance(p, str):
                text_parts.append(p)
        return "".join(text_parts)
    return str(parts)


def _sync_to_vertex_ai(project_id: str) -> None:
    """Sync local ADK results to the Vertex AI GenAI Evaluation Service.

    Uses the new ``vertexai.Client().evals`` API with agent-specific rubric
    metrics (FINAL_RESPONSE_QUALITY, TOOL_USE_QUALITY, HALLUCINATION, SAFETY).
    Falls back to the legacy ``EvalTask`` API if the new SDK is unavailable.
    """
    try:
        import pandas as pd  # noqa: F401
        import vertexai
    except ImportError:
        print("Vertex AI SDK or pandas not available. Skipping cloud sync.")
        return

    location = os.environ.get("AGENT_ENGINE_LOCATION", "us-central1")

    print("\nSyncing evaluation results to Vertex AI GenAI Evaluation Service...")
    vertexai.init(project=project_id, location=location)

    # Locate the latest ADK results directory
    all_run_dirs = []
    for adk_dir in [".adk", "deploy/.adk"]:
        if os.path.exists(adk_dir):
            all_run_dirs.extend(glob.glob(os.path.join(adk_dir, "*")))

    if not all_run_dirs:
        print("No ADK results found. Cannot sync to cloud.")
        return

    latest_run_dir = max(all_run_dirs, key=os.path.getmtime)
    print(f"  Found latest ADK run: {latest_run_dir}")

    data_files = glob.glob(os.path.join(latest_run_dir, "*.data.json"))
    if not data_files:
        print(f"  No .data.json files found in {latest_run_dir}")
        return

    # Try new Client API first, fall back to legacy EvalTask
    _sync_via_new_api = _try_new_eval_api(project_id, location, data_files)
    if not _sync_via_new_api:
        _sync_via_legacy_api(project_id, data_files)


def _try_new_eval_api(project_id: str, location: str, data_files: list[str]) -> bool:
    """Attempt sync using the new vertexai.Client().evals API.

    Returns True if successful, False if the API is not available.
    """
    try:
        from google.genai import types as genai_types
        from vertexai import Client
    except ImportError:
        return False

    try:
        client = Client(
            project=project_id,
            location=location,
            http_options=genai_types.HttpOptions(api_version="v1beta1"),
        )
    except Exception as e:
        print(f"  Could not create Vertex AI Client: {e}")
        return False

    gcs_dest = os.environ.get("EVAL_STORAGE_URI")
    if not gcs_dest:
        print(
            "  EVAL_STORAGE_URI not set. Skipping new-API cloud sync "
            "(GCS bucket required for evaluation results)."
        )
        return False

    for data_file in data_files:
        print(f"  Processing {Path(data_file).name} via new Eval API...")

        try:
            with open(data_file) as f:
                adk_data = json.load(f)

            eval_dataset = _transform_adk_results(adk_data)
            if not eval_dataset:
                print(f"    No valid items extracted from {Path(data_file).name}")
                continue

            import pandas as pd

            df = pd.DataFrame(eval_dataset)

            # Use agent-specific rubric metrics
            eval_run = client.evals.create_evaluation_run(
                dataset=df,
                metrics=[
                    "FINAL_RESPONSE_QUALITY",
                    "TOOL_USE_QUALITY",
                    "HALLUCINATION",
                    "SAFETY",
                ],
                dest=gcs_dest,
            )

            print(f"    Evaluation run created: {eval_run.name}")

        except Exception as e:
            print(f"    Error with new API for {Path(data_file).name}: {e}")

    return True


def _sync_via_legacy_api(project_id: str, data_files: list[str]) -> None:
    """Fall back to legacy vertexai.preview.evaluation.EvalTask API."""
    try:
        import pandas as pd
        from vertexai.preview.evaluation import EvalTask
    except ImportError:
        print("  Legacy Vertex AI evaluation API not available. Skipping cloud sync.")
        return

    for data_file in data_files:
        print(f"  Processing {Path(data_file).name} via legacy EvalTask...")

        try:
            with open(data_file) as f:
                adk_data = json.load(f)

            eval_dataset = _transform_adk_results(adk_data)
            if not eval_dataset:
                print(f"    No valid items extracted from {Path(data_file).name}")
                continue

            df = pd.DataFrame(eval_dataset)

            eval_task = EvalTask(
                dataset=df,
                metrics=[
                    "instruction_following",
                    "text_quality",
                ],
                experiment="sre-agent-evals",
            )

            eval_result = eval_task.evaluate()
            print(f"    Results for {Path(data_file).name}:")
            print(eval_result.summary_metrics)

        except Exception as e:
            print(f"    Error processing {Path(data_file).name}: {e}")


def _transform_adk_results(adk_data: list[dict]) -> list[dict]:
    """Transform ADK result data into a prompt/response dataset."""
    dataset = []
    for item in adk_data:
        prompt = "Unknown Prompt"
        response = ""

        if "test_case" in item:
            tc = item["test_case"]
            if "conversation" in tc:
                first_turn = tc["conversation"][0]
                prompt = _extract_text_from_parts(
                    first_turn.get("user_content", {}).get("parts", "")
                )
            elif "input" in tc:
                prompt = str(tc["input"])

        if "result" in item:
            res = item["result"]
            if "return_value" in res:
                response = str(res["return_value"])
            elif "error" in res:
                response = f"Error: {res['error']}"

        dataset.append({"prompt": prompt, "response": response})

    return dataset


def main():
    flags, should_sync, project_id_override = _parse_args(sys.argv[1:])
    project_id = _resolve_project_id(project_id_override)

    print(f"Using Google Cloud Project ID: {project_id}")

    with tempfile.TemporaryDirectory() as temp_dir:
        eval_files = _prepare_eval_files(project_id, temp_dir)
        result = _run_adk_eval(flags, eval_files)

        if should_sync:
            _sync_to_vertex_ai(project_id)
        else:
            print(
                "\nTip: Run with --sync to upload results to "
                "Vertex AI Evaluation console."
            )

        # Force a hard exit. Standard sys.exit() can hang waiting for
        # non-daemonic background threads started by cloud SDKs or gRPC.
        print(f"\nFinal Exit Code: {result.returncode}")
        sys.stdout.flush()
        os._exit(result.returncode)


if __name__ == "__main__":
    main()
