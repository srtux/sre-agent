import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None, env=None, interactive=False):
    """Runs a command and returns the output (or just runs it if interactive)."""
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
            print(line, end="")
            output.append(line)

    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd, "".join(output))

    return "".join(output)


def main():
    """Orchestrates the deployment of the full stack."""
    root_dir = Path(__file__).parent.parent

    print("🚀 STARTING FULL STACK DEPLOYMENT")
    print("=================================")

    # --- STEP 1: Deploy Backend to Vertex AI ---
    print("\n🏗️  Step 1: Deploying Backend (Vertex Agent Engine)...")
    try:
        backend_cmd = [sys.executable, "deploy/deploy.py", "--create"]
        # We MUST capture output to get the resource ID, but this might
        # fail if re-auth is needed. We recommend the user run 'gcloud auth login'
        # beforehand if they have session expiration issues.
        output = run_command(backend_cmd, cwd=str(root_dir))

        # Parse the resource name from output
        resource_name = None
        for line in output.splitlines():
            if "Resource Name:" in line:
                resource_name = line.split("Resource Name:")[1].strip()
                break
            # Fallback if the print statement is different
            if (
                "projects/" in line
                and "/locations/" in line
                and "/reasoningEngines/" in line
            ):
                resource_name = line.strip()
                break

        if not resource_name:
            print("❌ Failed to find backend resource name in output.")
            sys.exit(1)

        print(f"\n✅ Backend deployed! Resource URI: agentengine://{resource_name}")

        # --- STEP 2: Deploy Frontend to Cloud Run ---
        print("\n🏗️  Step 2: Deploying Frontend to Cloud Run...")

        # Construct the Agent Engine Query URL
        # Resource Name: projects/{project}/locations/{location}/reasoningEngines/{id}
        parts = resource_name.split("/")
        location = "us-central1"  # Default
        if "locations" in parts:
            idx = parts.index("locations")
            if idx + 1 < len(parts):
                location = parts[idx + 1]

        agent_url = (
            f"https://{location}-aiplatform.googleapis.com/v1/{resource_name}:query"
        )
        print(f"Connecting Frontend to Agent URL: {agent_url}")

        frontend_cmd = [
            sys.executable,
            "deploy/deploy_web.py",
            "--agent-url",
            agent_url,
            "--agent-id",
            resource_name,
        ]
        # Frontend deployment is primarily the heavy lifting, definitely allow interactivity.
        run_command(frontend_cmd, cwd=str(root_dir), interactive=True)

        print("\n🚀 FULL STACK DEPLOYMENT COMPLETE!")
        print(f"Backend (Vertex):  {resource_name}")
        print("Frontend (Flutter): Dashboard is ready!")

    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
