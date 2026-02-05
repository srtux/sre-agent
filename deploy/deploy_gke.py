import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd):
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"❌ Command failed with return code {result.returncode}")
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description="Deploy SRE Mission Control to GKE")
    parser.add_argument("--project-id", help="GCP Project ID")
    parser.add_argument("--cluster", required=True, help="GKE Cluster Name")
    parser.add_argument("--zone", help="GKE Cluster Zone")
    parser.add_argument("--region", help="GKE Cluster Region")
    parser.add_argument("--agent-id", help="Vertex Reasoning Engine resource ID")

    args = parser.parse_args()

    project_id = args.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ Error: GOOGLE_CLOUD_PROJECT not set.")
        sys.exit(1)

    agent_id = args.agent_id or os.getenv("SRE_AGENT_ID")
    if not agent_id:
        print("⚠️ Warning: SRE_AGENT_ID not provided. Agent will run in Local Mode.")

    # 1. Get GKE Credentials
    cred_cmd = [
        "gcloud",
        "container",
        "clusters",
        "get-credentials",
        args.cluster,
        f"--project={project_id}",
    ]
    if args.zone:
        cred_cmd.append(f"--zone={args.zone}")
    elif args.region:
        cred_cmd.append(f"--region={args.region}")
    else:
        print("❌ Error: Must provide --zone or --region.")
        sys.exit(1)
    run_command(cred_cmd)

    # 2. Create ConfigMap and Secrets
    print("\n🏗️ Creating Kubernetes ConfigMap and Secrets...")

    # ConfigMap
    run_command(
        [
            "kubectl",
            "create",
            "configmap",
            "autosre-config",
            f"--from-literal=project_id={project_id}",
            f"--from-literal=agent_id={agent_id or ''}",
            "--dry-run=client",
            "-o",
            "yaml",
            "|",
            "kubectl",
            "apply",
            "-f",
            "-",
        ]
    )

    # Note: For real production, use Secret Manager or external secret management.
    # This script assumes manual secret creation or retrieves them from local env for convenience.
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    encryption_key = os.getenv("SRE_AGENT_ENCRYPTION_KEY")
    client_id = os.getenv("GOOGLE_CLIENT_ID")

    if not (gemini_key and encryption_key and client_id):
        print(
            "⚠️ Missing secrets in local environment (GEMINI_API_KEY, SRE_AGENT_ENCRYPTION_KEY, GOOGLE_CLIENT_ID)."
        )
        print("👉 You may need to create 'autosre-secrets' manually in Kubernetes.")
    else:
        run_command(
            [
                "kubectl",
                "create",
                "secret",
                "generic",
                "autosre-secrets",
                f"--from-literal=gemini_api_key={gemini_key}",
                f"--from-literal=encryption_key={encryption_key}",
                f"--from-literal=google_client_id={client_id}",
                "--dry-run=client",
                "-o",
                "yaml",
                "|",
                "kubectl",
                "apply",
                "-f",
                "-",
            ]
        )

    # 3. Apply Manifests
    print("\n🚀 Applying GKE Manifests...")
    k8s_dir = Path("deploy/k8s")

    # Update image in deployment.yaml (using sed for simplicity in this script)
    image_name = f"gcr.io/{project_id}/autosre:latest"

    # Read, replace, and apply
    deploy_file = k8s_dir / "deployment.yaml"
    with open(deploy_file) as f:
        content = f.read().replace("gcr.io/PROJECT_ID/autosre:latest", image_name)

    process = subprocess.Popen(["kubectl", "apply", "-f", "-"], stdin=subprocess.PIPE)
    process.communicate(input=content.encode())

    run_command(["kubectl", "apply", "-f", str(k8s_dir / "service.yaml")])

    print("\n✅ Deployment to GKE initiated!")
    print("🔗 Run 'kubectl get service autosre' to find your LoadBalancer IP.")


if __name__ == "__main__":
    main()
