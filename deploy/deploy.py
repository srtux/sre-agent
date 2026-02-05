"""Deployment script for SRE Agent"""

import os
import re
import sys
import time
from pathlib import Path

try:
    import cloudpickle
except ImportError:
    cloudpickle = None

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

# Guard against global objects being initialized during pickling
os.environ["SRE_AGENT_DEPLOYMENT_MODE"] = "true"

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
flags.DEFINE_bool(
    "use_agent_identity", False, "Enable Agent Identity for the Reasoning Engine."
)


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
    """Reads requirements from pyproject.toml with robust merging and sanitization."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    # Get dependencies from [project] section
    dependencies = pyproject.get("project", {}).get("dependencies", [])

    # Ensure crucial deployment dependencies are present
    # Pinned to exact versions found in local environment/lock file for stability
    required_for_deploy = [
        "google-adk==1.23.0",
        "google-cloud-aiplatform==1.134.0",
        "google-genai==1.59.0",
        "opentelemetry-instrumentation-google-genai==0.6b0",
        "pydantic==2.12.5",
        "requests>=2.31.0",
        "mcp==1.25.0",
        "python-dotenv>=1.0.1",
    ]

    # Map of package name (lowercase) to full requirement string
    req_map = {}

    # List of dependencies to exclude from Agent Engine deployment
    exclude_from_deploy = {
        "fastapi",
        "uvicorn",
        "opentelemetry-instrumentation-fastapi",
        "starlette",
        "anyio",
        "sniffio",
        "deptry",
        "ruff",
        "mypy",
        "pydantic-core",  # Let pydantic handle its core
        "pydantic-settings",
    }

    def add_req(req_str: str):
        import re

        # Handle markers if present
        cleaned_req = req_str
        if ";" in req_str:
            base, marker = req_str.split(";", 1)
            if "python_version < '3.11'" in marker and sys.version_info >= (3, 11):
                return
            cleaned_req = base.strip()

        # Extract name
        name = re.split(r"[>=<~!\[]", cleaned_req)[0].lower().strip()

        if name in exclude_from_deploy:
            return

        req_map[name] = cleaned_req

    # Process existing dependencies
    for d in dependencies:
        add_req(d)

    # Merge/Override with pinned deployment packages
    for r in required_for_deploy:
        name = re.split(r"[>=<~!\[]", r)[0].lower().strip()
        req_map[name] = r

    # Explicitly add cloudpickle
    if "cloudpickle" not in req_map and cloudpickle:
        req_map["cloudpickle"] = f"cloudpickle=={cloudpickle.__version__}"

    return sorted(list(req_map.values()))


def clean_package_folders():
    """Removes __pycache__ and .pyc files recursively to avoid build/loading issues."""
    print("Cleaning __pycache__ and stale build artifacts...")
    base_dir = Path(__file__).parent.parent / "sre_agent"
    import shutil

    for path in base_dir.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)
    for path in base_dir.rglob("*.pyc"):
        path.unlink()
    for path in base_dir.rglob("*.pyo"):
        path.unlink()


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

    adk_app = AdkApp(agent=adapter)

    requirements = get_requirements()
    display_name = FLAGS.display_name if FLAGS.display_name else root_agent.name
    description = FLAGS.description if FLAGS.description else root_agent.description

    # Re-initialize display_name/description if they weren't set correctly above
    # (Cleaning up a previous small edit error)

    # Ensure staging bucket has gs:// prefix for the client-scoped API
    staging_bucket = (
        FLAGS.bucket if FLAGS.bucket else os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
    )
    if staging_bucket and not staging_bucket.startswith("gs://"):
        staging_bucket = f"gs://{staging_bucket}"

    # Identify the API and identity settings
    if getattr(FLAGS, "use_agent_identity", False) is True:
        from vertexai import types

        client = vertexai.Client(
            project=FLAGS.project_id or os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=FLAGS.location
            or os.getenv("AGENT_ENGINE_LOCATION")
            or os.getenv("GOOGLE_CLOUD_LOCATION"),
            http_options=dict(api_version="v1beta1"),
        )
        agent_engines_api = client.agent_engines
        print("✅ Using v1beta1 client for Agent Identity")
        print("🔐 Agent Identity enabled for this deployment.")
        identity_config = {"identity_type": types.IdentityType.AGENT_IDENTITY}
    else:
        agent_engines_api = agent_engines
        identity_config = {}

    # Find existing agent by Resource ID or Display Name
    existing_agent = None
    if FLAGS.resource_id:
        print(f"Checking for existing agent with ID: {FLAGS.resource_id}")
        try:
            existing_agent = agent_engines_api.get(FLAGS.resource_id)
        except Exception:
            print(f"Agent with ID {FLAGS.resource_id} not found.")

    if not existing_agent and not getattr(FLAGS, "force_new", False):
        print(f"Searching for existing agent with display name '{display_name}'...")
        try:
            all_agents = agent_engines_api.list()
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
            "ADK_OTEL_TO_CLOUD": "true",
            # We rely on ADK's native exporters in the Agent Engine runtime.
            # Manual OTEL_TO_CLOUD is disabled to avoid duplicate span conflicts.
            "OTEL_SERVICE_NAME": "sre-agent",
            "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED": "true",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
            "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS": "false",
            "USE_ARIZE": "false",
            "RUNNING_IN_AGENT_ENGINE": "true",
            "LOG_FORMAT": "JSON",
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            "STRICT_EUC_ENFORCEMENT": os.getenv("STRICT_EUC_ENFORCEMENT", "false"),
            "SRE_AGENT_ENFORCE_POLICY": os.getenv("SRE_AGENT_ENFORCE_POLICY", "true"),
            "SRE_AGENT_ENCRYPTION_KEY": os.getenv("SRE_AGENT_ENCRYPTION_KEY", ""),
            **env_vars,
        },
    }

    if identity_config:
        common_kwargs["config"] = identity_config

    # IMPORTANT: Propagate the stable Agent ID to the backend if we are updating.
    # This ensures that the backend uses the correct app_name for sessions.
    if existing_agent and not FLAGS.force_new:
        existing_resource_name = getattr(
            existing_agent, "resource_name", None
        ) or getattr(getattr(existing_agent, "api_resource", None), "name", "unknown")
        common_kwargs["env_vars"]["SRE_AGENT_ID"] = existing_resource_name

    print(f"Deploying with requirements: {requirements}")

    if existing_agent and not FLAGS.force_new:
        print(f"✅ Found existing agent: {existing_agent.resource_name}")
        print("🚀 Updating existing agent (patching)...")

        # Handle concurrent updates with a retry loop
        max_retries = 12  # 12 * 60s = 12 minutes
        retry_count = 0
        from google.api_core import exceptions

        while retry_count < max_retries:
            try:
                if getattr(FLAGS, "use_agent_identity", False) is True:
                    # Packaging for client.agent_engines.update
                    update_config = common_kwargs.get("config", {}).copy()
                    update_config.update(
                        {
                            "display_name": display_name,
                            "description": description,
                            "staging_bucket": staging_bucket,
                        }
                    )

                    remote_agent = agent_engines_api.update(
                        name=existing_agent.resource_name,
                        agent=adk_app,
                        config=update_config,
                    )
                else:
                    # ReasoningEngine.update uses top-level arguments
                    # Standard ReasoningEngine.update does NOT accept staging_bucket.
                    # Use 'agent_engine' matching the current SDK signature
                    remote_agent = existing_agent.update(
                        agent_engine=adk_app,
                        display_name=display_name,
                        description=description,
                        **common_kwargs,
                    )
                remote_resource_name = getattr(
                    remote_agent, "resource_name", None
                ) or getattr(
                    getattr(remote_agent, "api_resource", None), "name", "unknown"
                )
                print(f"Successfully updated agent: {remote_resource_name}")
                break
            except exceptions.InvalidArgument as e:
                error_msg = str(e)
                if "Build failed" in error_msg:
                    print(f"❌ Permanent Build Failure detected: {error_msg}")
                    print(
                        "Hint: This often means a requirement is missing or incompatible."
                    )
                    print("Review requirements.txt and code for errors.")
                    raise

                # Vertex AI often returns 400 InvalidArgument when an update is already in progress
                retry_count += 1
                if retry_count < max_retries:
                    print(
                        f"⚠️  Concurrent update detected or invalid state. Retrying in 60s ({retry_count}/{max_retries})..."
                    )
                    print(f"Error detail: {error_msg}")
                    time.sleep(60)
                else:
                    print("❌ Maximum retries reached. Failing deployment.")
                    raise
            except Exception as e:
                print(f"❌ Unexpected error during update: {e}")
                raise
    else:
        print(f"🚀 Creating new agent: {display_name}")
        if getattr(FLAGS, "use_agent_identity", False) is True:
            # Packaging for client.agent_engines.create
            create_config = common_kwargs.get("config", {}).copy()
            create_config.update(
                {
                    "display_name": display_name,
                    "description": description,
                    "requirements": common_kwargs.get("requirements"),
                    "extra_packages": common_kwargs.get("extra_packages"),
                    "env_vars": common_kwargs.get("env_vars"),
                    # Service account must be unset when using AGENT_IDENTITY
                    "min_instances": FLAGS.min_instances,
                    "max_instances": FLAGS.max_instances,
                    "staging_bucket": staging_bucket,
                }
            )
            remote_agent = agent_engines_api.create(
                agent=adk_app,
                config=create_config,
            )
        else:
            # ReasoningEngine.create uses top-level arguments
            # We don't pass staging_bucket to ReasoningEngine.create directly as it uses vertexai.init
            # Use 'agent_engine' instead of 'agent' for modern SDK compatibility.
            remote_agent = agent_engines_api.create(
                agent_engine=adk_app,
                display_name=display_name,
                description=description,
                **common_kwargs,
                service_account=FLAGS.service_account,
                min_instances=FLAGS.min_instances,
                max_instances=FLAGS.max_instances,
            )
        print(f"Successfully created agent: {display_name}")

    remote_resource_name = getattr(remote_agent, "resource_name", None) or getattr(
        getattr(remote_agent, "api_resource", None), "name", "unknown"
    )
    print(f"Resource name: {remote_resource_name}")


def delete(resource_id: str) -> None:
    # Use global agent_engines for delete unless we want to scope it too
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

    # Re-initialize client if Agent Identity is requested to ensure v1beta1 support
    if FLAGS.use_agent_identity:
        # Client initialization moved inside deploy() for cleaner scoping
        pass

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
