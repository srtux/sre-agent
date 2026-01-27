"""Deployment script for SRE Agent"""

import os
import re
import sys
import time
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# ruff: noqa: E402
# Enable JSON Schema for function declarations to fix Vertex AI API compatibility
# This ensures tool schemas use camelCase (additionalProperties) instead of snake_case
# Must be done BEFORE importing the agent to ensure tools are registered correctly
from google.adk.features import FeatureName, override_feature_enabled

override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, True)
print("✅ Enabled JSON_SCHEMA_FOR_FUNC_DECL feature for Vertex AI compatibility")

import vertexai
from absl import app, flags
from dotenv import load_dotenv
from vertexai import agent_engines
from vertexai.agent_engines import AdkApp

from sre_agent.agent import root_agent
from sre_agent.core.runner import create_runner
from sre_agent.core.runner_adapter import RunnerAgentAdapter

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket.")
flags.DEFINE_string("resource_id", None, "ReasoningEngine resource ID.")
flags.DEFINE_string("display_name", None, "Display name for the agent.")
flags.DEFINE_string("description", None, "Description for the agent.")
flags.DEFINE_string("service_account", None, "Service account for the agent.")
flags.DEFINE_integer("min_instances", 1, "Minimum instances.")
flags.DEFINE_integer("max_instances", None, "Maximum instances.")


flags.DEFINE_bool("list", False, "List all agents.")
flags.DEFINE_bool("create", False, "Deploy or update an agent.")
flags.DEFINE_bool("delete", False, "Deletes an existing agent.")
flags.DEFINE_bool("verify", True, "Verify agent import before creation.")
flags.DEFINE_bool(
    "force_new",
    False,
    "Force creation of a new agent even if one exists with the same name.",
)
flags.mark_bool_flags_as_mutual_exclusive(["create", "delete"])


def get_requirements() -> list[str]:
    """Reads requirements from pyproject.toml with robust merging."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    # Get dependencies from [project] section
    dependencies = pyproject.get("project", {}).get("dependencies", [])

    # Ensure crucial deployment dependencies are present
    # These are required by the Reasoning Engine runtime itself
    required_for_deploy = [
        "google-adk>=1.23.0",
        "google-cloud-aiplatform[adk,agent-engines]>=1.93.0",
        "requests>=2.31.0",
    ]

    # Map of package name (lowercase) to full requirement string
    req_map = {}

    def add_req(req_str: str):
        # Extract package name for comparison (e.g., 'google-adk>=1.0' -> 'google-adk')
        import re

        name = re.split(r"[>=<~!\[]", req_str)[0].lower().strip()
        req_map[name] = req_str

    # Process existing dependencies first
    for d in dependencies:
        add_req(d)

    # Merge required deployment packages if not already present
    for r in required_for_deploy:
        name = re.split(r"[>=<~!\[]", r)[0].lower().strip()
        if name not in req_map:
            req_map[name] = r

    return list(req_map.values())


def verify_local_import():
    """Verify that the agent can be imported locally without error."""
    print("Checking if agent is importable locally...")
    try:
        from sre_agent.agent import root_agent
        from sre_agent.core.runner import create_runner
        from sre_agent.core.runner_adapter import RunnerAgentAdapter

        # Verify we can wrap the agent
        runner = create_runner(root_agent)
        adapter = RunnerAgentAdapter(runner, name=root_agent.name)

        print(f"✅ Successfully imported and wrapped agent: {adapter.name}")
        return True
    except ImportError as e:
        print(f"❌ ERROR: Failed to import agent locally: {e}")
        print("Please ensure all dependencies in pyproject.toml are installed.")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error during agent import: {e}")
        return False


def deploy(env_vars: dict[str, str] | None = None) -> None:
    """Deploys or updates an agent engine for SRE Agent."""
    if env_vars is None:
        env_vars = {}

    # Wrap agent in Runner for remote deployment to ensure
    # stateless execution, policy enforcement, and context compaction.
    runner = create_runner(root_agent)
    adapter = RunnerAgentAdapter(runner, name=root_agent.name)

    adk_app = AdkApp(agent=adapter, enable_tracing=True)

    requirements = get_requirements()
    display_name = FLAGS.display_name if FLAGS.display_name else root_agent.name
    description = FLAGS.description if FLAGS.description else root_agent.description

    # Find existing agent by Resource ID or Display Name
    existing_agent = None
    if FLAGS.resource_id:
        print(f"Checking for existing agent with ID: {FLAGS.resource_id}")
        try:
            existing_agent = agent_engines.get(FLAGS.resource_id)
        except Exception:
            print(f"Agent with ID {FLAGS.resource_id} not found.")

    if not existing_agent and not FLAGS.force_new:
        print(f"Searching for existing agent with display name '{display_name}'...")
        try:
            all_agents = agent_engines.list()
            for agent in all_agents:
                if agent.display_name == display_name:
                    existing_agent = agent
                    break
        except Exception as e:
            print(f"Note: Could not list agents: {e}")

    common_kwargs = {
        "requirements": requirements,
        "extra_packages": ["./sre_agent"],
        "env_vars": {
            "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
            "USE_ARIZE": "false",
            "RUNNING_IN_AGENT_ENGINE": "true",
            "LOG_FORMAT": "JSON",
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            "STRICT_EUC_ENFORCEMENT": os.getenv("STRICT_EUC_ENFORCEMENT", "false"),
            "SRE_AGENT_ENCRYPTION_KEY": os.getenv("SRE_AGENT_ENCRYPTION_KEY", ""),
            **env_vars,
        },
    }

    # IMPORTANT: Propagate the stable Agent ID to the backend if we are updating.
    # This ensures that the backend uses the correct app_name for sessions.
    if existing_agent and not FLAGS.force_new:
        common_kwargs["env_vars"]["SRE_AGENT_ID"] = existing_agent.resource_name

    print(f"Deploying with requirements: {requirements}")

    if existing_agent and not FLAGS.force_new:
        print(f"✅ Found existing agent: {existing_agent.resource_name}")
        print("🚀 Updating existing agent (patching)...")
        # In the ADK/Vertex SDK, update() performs the PATCH operation
        # Note: update() requires all arguments to be keyword-only

        # Handle concurrent updates with a retry loop
        max_retries = 12  # 12 * 60s = 12 minutes
        retry_count = 0
        from google.api_core import exceptions

        while retry_count < max_retries:
            try:
                remote_agent = existing_agent.update(
                    agent_engine=adk_app,
                    display_name=display_name,
                    description=description,
                    **common_kwargs,
                )
                print(f"Successfully updated agent: {remote_agent.resource_name}")
                break
            except exceptions.InvalidArgument as e:
                # Vertex AI often returns 400 InvalidArgument when an update is already in progress
                retry_count += 1
                if retry_count < max_retries:
                    print(
                        f"⚠️  Concurrent update detected or invalid state. Retrying in 60s ({retry_count}/{max_retries})..."
                    )
                    print(f"Error detail: {e}")
                    time.sleep(60)
                else:
                    print("❌ Maximum retries reached. Failing deployment.")
                    raise
            except Exception as e:
                print(f"❌ Unexpected error during update: {e}")
                raise
    else:
        print(f"🚀 Creating new agent: {display_name}")
        remote_agent = agent_engines.create(
            agent_engine=adk_app,
            display_name=display_name,
            description=description,
            **common_kwargs,
            service_account=FLAGS.service_account,
            min_instances=FLAGS.min_instances,
            max_instances=FLAGS.max_instances,
        )
        print(f"Successfully created agent: {remote_agent.resource_name}")

    print(f"Resource name: {remote_agent.resource_name}")


def delete(resource_id: str) -> None:
    remote_agent = agent_engines.get(resource_id)
    remote_agent.delete(force=True)
    print(f"Deleted remote agent: {resource_id}")


def list_agents() -> None:
    remote_agents = agent_engines.list()
    if not remote_agents:
        print("No remote agents found.")
        return

    template = """
{agent.name} ("{agent.display_name}")
- Resource Name: {agent.resource_name}
- Create time: {agent.create_time}
- Update time: {agent.update_time}
"""
    remote_agents_string = "".join(
        template.format(agent=agent) for agent in remote_agents
    )
    print(f"All remote agents:\n{remote_agents_string}")


def main(argv: list[str]) -> None:
    del argv  # unused
    load_dotenv()

    project_id = (
        FLAGS.project_id if FLAGS.project_id else os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    location = (
        FLAGS.location
        or os.getenv("AGENT_ENGINE_LOCATION")
        or os.getenv("GOOGLE_CLOUD_LOCATION")
    )
    bucket = FLAGS.bucket if FLAGS.bucket else os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")

    print(f"PROJECT: {project_id}")
    print(f"LOCATION: {location}")
    print(f"BUCKET: {bucket}")

    if not project_id:
        print("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
        return
    elif not location:
        print("Missing required environment variable: GOOGLE_CLOUD_LOCATION")
        return
    elif not bucket:
        print("Missing required environment variable: GOOGLE_CLOUD_STORAGE_BUCKET")
        return

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=bucket if bucket.startswith("gs://") else f"gs://{bucket}",
    )

    if FLAGS.list:
        list_agents()
    elif FLAGS.create:
        env_vars: dict[str, str] = {}

        if FLAGS.verify:
            if not verify_local_import():
                print("Aborting deployment due to local import failure.")
                return

        # Add location variables to deployment environment
        # Note: GOOGLE_CLOUD_LOCATION is reserved by Vertex AI Agent Engine
        env_vars["GCP_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION", "")
        env_vars["AGENT_ENGINE_LOCATION"] = os.getenv("AGENT_ENGINE_LOCATION", "")
        env_vars["GCP_PROJECT_ID"] = project_id or ""

        deploy(env_vars=env_vars)
    elif FLAGS.delete:
        if not FLAGS.resource_id:
            print("resource_id is required for delete")
            return
        delete(FLAGS.resource_id)
    else:
        print("Unknown command")


if __name__ == "__main__":
    app.run(main)
