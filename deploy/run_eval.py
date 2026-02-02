#!/usr/bin/env python3
import glob
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
load_dotenv()


def main():
    # Separate flags from positional arguments
    all_args = sys.argv[1:]
    flags = []

    # Check if we should sync to cloud (not standard for local runs - it's slow!)
    should_sync_cloud = "--sync" in all_args

    i = 0
    while i < len(all_args):
        arg = all_args[i]
        if arg == "--sync":
            i += 1
            continue
        if arg.startswith("-"):
            flags.append(arg)
            # If next arg exists and doesn't start with '-', it's likely a value for this flag
            if i + 1 < len(all_args) and not all_args[i + 1].startswith("-"):
                flags.append(all_args[i + 1])
                i += 1
        i += 1

    # Define our standard agent
    agent_path = "sre_agent"

    # Get project ID from env
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")

    # Sanitize if it's comma-separated
    if project_id and "," in project_id:
        project_id = project_id.split(",")[0].strip()
        # Update env so subprocess sees clean value
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    if not project_id:
        print(
            "WARNING: GOOGLE_CLOUD_PROJECT not set in .env. Using 'my-test-project' as fallback."
        )
        project_id = "my-test-project"

    print(f"Using Google Cloud Project ID: {project_id}")

    # Process eval files to substitute placeholder
    original_eval_files = glob.glob("eval/*.test.json")

    # Create a temporary directory for processed eval files
    with tempfile.TemporaryDirectory() as temp_dir:
        processed_eval_files = []

        for file_path in original_eval_files:
            try:
                with open(file_path) as f:
                    content = f.read()

                # key substitution
                modified_content = content.replace("TEST_PROJECT_ID", project_id)

                # Write to temp dir
                file_name = Path(file_path).name
                temp_file_path = os.path.join(temp_dir, file_name)

                with open(temp_file_path, "w") as f:
                    f.write(modified_content)

                processed_eval_files.append(temp_file_path)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                # Fallback to original file if processing fails
                processed_eval_files.append(file_path)

        # Construct the command with flags BEFORE positional arguments
        # adk eval [FLAGS] [AGENT] [FILES]
        cmd = ["adk", "eval", *flags]

        # Add config file if it exists
        config_path = "eval/test_config.json"
        if os.path.exists(config_path):
            cmd.extend(["--config_file_path", config_path])

        cmd.extend([agent_path, *processed_eval_files])

        # Add storage URI if provided in env
        storage_uri = os.environ.get("EVAL_STORAGE_URI")
        if storage_uri:
            cmd.extend(["--eval_storage_uri", storage_uri])

        # 1. Run the local/ADK evaluation
        print(f"🚀 Running ADK Eval: {' '.join(cmd)}")
        sys.stdout.flush()

        result = subprocess.run(cmd)

        # 2. Trigger the cloud-native Vertex AI Agent Evaluation Service (Optional)
        if should_sync_cloud:
            try:
                import vertexai
                from vertexai.preview.evaluation import EvalTask

                print(
                    "\n📡 Triggering Vertex AI GenAI Evaluation Service for Cloud UI sync (this executes the evaluation again in the cloud)..."
                )
                vertexai.init(
                    project=project_id,
                    location=os.environ.get("AGENT_ENGINE_LOCATION", "us-central1"),
                )

                # trigger the cloud-native evaluation service for each file
                for processed_file in processed_eval_files:
                    print(f"  - Syncing {Path(processed_file).name}...")
                    EvalTask(
                        dataset=processed_file,
                        metrics=[
                            "trajectory_exact_match",
                            "trajectory_precision",
                            "trajectory_recall",
                            "groundedness",
                        ],
                        experiment="sre-agent-evals",
                    ).evaluate()

                print(
                    "✅ Cloud Evaluation complete. Results available in Vertex AI Console."
                )
            except ImportError:
                print(
                    "💡 Vertex AI SDK 'preview.evaluation' not available. Skipping cloud sync."
                )
            except Exception as e:
                print(f"⚠️ Could not trigger Vertex AI service: {e}")
        else:
            print(
                "\n💡 Tip: Run with --sync to upload results to Vertex AI Evaluation console (slow)."
            )

        # Force a hard exit. Standard sys.exit() can hang waiting for
        # non-daemonic background threads started by cloud SDKs or gRPC.
        print(f"\nFinal Exit Code: {result.returncode}")
        sys.stdout.flush()
        os._exit(result.returncode)


if __name__ == "__main__":
    main()
