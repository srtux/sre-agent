#!/usr/bin/env python3
import glob
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main():
    # Separate flags from positional arguments
    # Everything starting with '-' is a flag
    flags = [arg for arg in sys.argv[1:] if arg.startswith("-")]

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

        # Disable OTel export for local evaluations to avoid noise/errors
        env = os.environ.copy()
        env["OTEL_TRACES_EXPORTER"] = "none"
        env["OTEL_METRICS_EXPORTER"] = "none"
        env["OTEL_LOGS_EXPORTER"] = "none"

        # 1. Run the local/ADK evaluation
        print(f"Running ADK Eval: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env)

        # 2. Trigger the cloud-native Vertex AI Agent Evaluation Service (Latest features)
        # This makes the results appear in Vertex AI > Evaluations & Experiments console
        try:
            import vertexai
            from vertexai.preview.evaluation import EvalTask

            # Use the bucket from env for storage
            bucket = os.environ.get(
                "GOOGLE_CLOUD_STORAGE_BUCKET", os.environ.get("STAGING_BUCKET")
            )
            if bucket:
                print(
                    "📡 Triggering Vertex AI GenAI Evaluation Service (Experiment: sre-agent-evals)..."
                )
                vertexai.init(
                    project=project_id,
                    location=os.environ.get("AGENT_ENGINE_LOCATION", "us-central1"),
                )

                # trigger the cloud-native evaluation service
                EvalTask(
                    dataset=processed_eval_files[0],
                    metrics=["trajectory_exact_match", "trajectory_precision"],
                    experiment="sre-agent-evals",
                ).evaluate()

                print(
                    "✅ Cloud Evaluation request sent. Results available in Vertex AI Console."
                )
        except ImportError:
            print(
                "💡 Vertex AI SDK 'preview.evaluation' not available. Skipping cloud-tab sync."
            )
        except Exception as e:
            print(f"⚠️ Could not trigger Vertex AI service: {e}")

        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
