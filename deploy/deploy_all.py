import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None, env=None, interactive=False, prefix=None):
    """Runs a command and returns the output (or just runs it if interactive)."""
    if prefix:
        print(f"[{prefix}] Executing: {' '.join(cmd)}")
    else:
        print(f"Executing: {' '.join(cmd)}")

    if interactive:
        # Inherit TTY for authentication/interaction
        return subprocess.run(
            cmd, cwd=cwd, env={**os.environ, **(env or {})}, check=True
        )

    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    output = []
    if process.stdout:
        for line in process.stdout:
            if prefix:
                print(f"[{prefix}] {line}", end="")
            else:
                print(line, end="")
            output.append(line)

    process.wait()
    if process.returncode != 0:
        if prefix:
            print(f"[{prefix}] ❌ Command failed with return code {process.returncode}")
        raise subprocess.CalledProcessError(process.returncode, cmd, "".join(output))

    return "".join(output)


def get_existing_agent_id():
    """Quickly check for an existing agent by name."""
    try:
        import vertexai
        from dotenv import load_dotenv
        from vertexai import agent_engines

        load_dotenv()
        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        location = (
            os.getenv("AGENT_ENGINE_LOCATION")
            or os.getenv("GOOGLE_CLOUD_LOCATION")
            or "us-central1"
        )

        if not project:
            return None

        vertexai.init(project=project, location=location)
        agents = agent_engines.list()
        for agent in agents:
            if agent.display_name == "sre_agent":
                return agent.resource_name
        return None
    except Exception:
        return None


def main():
    """Orchestrates the deployment of the full stack."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Deploy SRE Mission Control full stack"
    )
    parser.add_argument(
        "--allow-unauthenticated",
        action="store_true",
        help="Allow unauthenticated access to Cloud Run (public access)",
    )
    args = parser.parse_args()

    root_dir = Path(__file__).parent.parent

    print("🚀 STARTING FULL STACK DEPLOYMENT")
    print("=================================")

    # --- OPTIMIZATION: Check for existing agent for parallel deployment ---
    print("\n🔍 Checking for existing stable Backend ID...")
    existing_resource_id = get_existing_agent_id()

    if existing_resource_id:
        print(f"✅ Found stable Backend ID: {existing_resource_id}")
        print("🚀 PARALLEL DEPLOYMENT INITIATED (Patching existing agent)")
        print("=========================================================")

        parts = existing_resource_id.split("/")
        location = "us-central1"
        if "locations" in parts:
            idx = parts.index("locations")
            if idx + 1 < len(parts):
                location = parts[idx + 1]

        agent_url = f"https://{location}-aiplatform.googleapis.com/v1/{existing_resource_id}:query"

        # Track A: Backend (Parallel)
        backend_cmd = [sys.executable, "deploy/deploy.py", "--create"]

        # Track B: Frontend (Parallel)
        frontend_cmd = [
            sys.executable,
            "deploy/deploy_web.py",
            "--agent-url",
            agent_url,
            "--agent-id",
            existing_resource_id,
        ]
        if args.allow_unauthenticated:
            frontend_cmd.append("--allow-unauthenticated")

        import threading

        def run_backend():
            try:
                run_command(backend_cmd, cwd=str(root_dir), prefix="BACKEND")
                print("\n[BACKEND] ✅ Backend patch complete.")
            except Exception as e:
                print(f"\n[BACKEND] ❌ Backend deployment failed: {e}")
                # We don't exit here to let the other track finish or report

        def run_frontend():
            try:
                # Use interactive=True if possible, but for parallel we might prefer prefixing
                run_command(frontend_cmd, cwd=str(root_dir), prefix="FRONTEND")
                print("\n[FRONTEND] ✅ Frontend deployment complete.")
            except Exception as e:
                print(f"\n[FRONTEND] ❌ Frontend deployment failed: {e}")

        t1 = threading.Thread(target=run_backend)
        t2 = threading.Thread(target=run_frontend)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        print("\n🚀 PARALLEL DEPLOYMENT PROCESS FINISHED!")
        return

    # --- FALLBACK: Sequential Deployment (for new agents) ---
    print(
        "\n⚠️  No existing agent found or error checking. Running SEQUENTIAL deployment..."
    )
    print("🏗️  Step 1: Deploying Backend (Vertex Agent Engine)...")
    try:
        backend_cmd = [sys.executable, "deploy/deploy.py", "--create"]
        output = run_command(backend_cmd, cwd=str(root_dir))

        resource_name = None
        for line in output.splitlines():
            if "Resource name:" in line:
                resource_name = line.split("Resource name:")[1].strip()
                break
            if "Resource Name:" in line:
                resource_name = line.split("Resource Name:")[1].strip()
                break

        if not resource_name:
            import re

            pattern = r"projects/[^/]+/locations/[^/]+/reasoningEngines/[^/\s]+"
            for line in output.splitlines():
                match = re.search(pattern, line)
                if match and "/operations/" not in line:
                    resource_name = match.group(0)
                    break

        if not resource_name:
            print("❌ Failed to find backend resource name in output.")
            sys.exit(1)

        print(f"\n✅ Backend deployed! Resource URI: agentengine://{resource_name}")

        print("\n🏗️  Step 2: Deploying Frontend to Cloud Run...")
        parts = resource_name.split("/")
        location = "us-central1"
        if "locations" in parts:
            idx = parts.index("locations")
            if idx + 1 < len(parts):
                location = parts[idx + 1]

        agent_url = (
            f"https://{location}-aiplatform.googleapis.com/v1/{resource_name}:query"
        )

        frontend_cmd = [
            sys.executable,
            "deploy/deploy_web.py",
            "--agent-url",
            agent_url,
            "--agent-id",
            resource_name,
        ]
        if args.allow_unauthenticated:
            frontend_cmd.append("--allow-unauthenticated")

        run_command(frontend_cmd, cwd=str(root_dir), interactive=True)

        print("\n🚀 SEQUENTIAL DEPLOYMENT COMPLETE!")
        print(f"Backend (Vertex):  {resource_name}")
        print("Frontend (Flutter): Dashboard is ready!")

    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
