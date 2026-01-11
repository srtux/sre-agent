import os
import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None, env=None):
    """Runs a command and returns the output."""
    print(f"Executing: {' '.join(cmd)}")
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

    full_output = []
    for line in iter(process.stdout.readline, ""):
        print(line, end="")
        full_output.append(line)

    process.stdout.close()
    return_code = process.wait()

    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, cmd, "".join(full_output))

    return "".join(full_output)


def main():
    root_dir = Path(__file__).parent.parent

    print("🏗️  Step 1: Deploying Backend to Vertex Agent Engine...")
    try:
        # Run the existing backend deploy script
        backend_output = run_command(
            [sys.executable, "deploy/deploy.py", "--create"], cwd=str(root_dir)
        )

        # Extract the resource name using regex
        # Based on: "Created remote agent: projects/XYZ/locations/L/reasoningEngines/123"
        match = re.search(
            r"Created remote agent: (projects/[^/]+/locations/[^/]+/reasoningEngines/\d+)",
            backend_output,
        )
        if not match:
            # Try a simpler match for just the ID if full path isn't found
            match = re.search(r"Created remote agent: (\d+)", backend_output)

        if not match:
            print(
                "❌ Error: Could not extract Reasoning Engine resource name from backend deployment output."
            )
            sys.exit(1)

        resource_name = match.group(1)
        # Construct the ADK-compatible URI
        agent_uri = f"agentengine://{resource_name}"
        print(f"\n✅ Backend deployed! Resource URI: {agent_uri}")

    except Exception as e:
        print(f"\n❌ Backend deployment failed: {e}")
        sys.exit(1)

    print("\n🏗️  Step 2: Deploying Frontend to Cloud Run...")
    try:
        # Run the web deploy script, passing the agent URI
        frontend_cmd = [
            sys.executable,
            "deploy/deploy_web.py",
            "--agent-url",
            agent_uri,
        ]
        run_command(frontend_cmd, cwd=str(root_dir))

        print("\n🚀 FULL STACK DEPLOYMENT COMPLETE!")
        print(f"Backend: {resource_name}")
        print(f"Frontend: Pointing to {agent_uri}")

    except Exception as e:
        print(f"\n❌ Frontend deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
