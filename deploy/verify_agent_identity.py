import argparse
import os
import subprocess
import sys

import vertexai


def run_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def main():
    parser = argparse.ArgumentParser(description="Verify Agent Identity Setup")
    parser.add_argument(
        "--agent-id", required=True, help="Numeric ID of the Agent Engine"
    )
    parser.add_argument("--project", help="GCP Project ID (optional)")
    parser.add_argument("--location", default="us-central1", help="GCP Location")
    args = parser.parse_args()

    project_id = args.project or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print(
            "❌ Error: Project ID not found. Use --project or set GOOGLE_CLOUD_PROJECT."
        )
        sys.exit(1)

    print(
        f"🔍 Verifying Agent Identity for Agent ID: {args.agent_id} in {project_id}..."
    )

    # 1. Fetch Agent Engine details using v1beta1
    try:
        client = vertexai.Client(
            project=project_id,
            location=args.location,
            http_options={"api_version": "v1beta1"},
        )
        engine_name = f"projects/{project_id}/locations/{args.location}/reasoningEngines/{args.agent_id}"
        engine = client.agent_engines.get(name=engine_name)

        # Accessing the spec directly from the api_resource (ReasoningEngine proto)
        api_resource = getattr(engine, "api_resource", None)
        if api_resource:
            spec = getattr(api_resource, "spec", {})
            # spec is likely a dict or an object depending on version
            if hasattr(spec, "identity_type"):
                identity_type = spec.identity_type
                effective_identity = spec.effective_identity
            else:
                identity_type = spec.get("identityType")
                effective_identity = spec.get("effectiveIdentity")
        else:
            print("⚠️ Warning: Could not access api_resource.")
            identity_type = "UNKNOWN"
            effective_identity = None

        print(
            f"✅ Agent Engine Found: {getattr(api_resource, 'display_name', 'Unknown')}"
        )
        print(f"🆔 Identity Type: {identity_type}")
        print(f"👤 Effective Identity: {effective_identity}")

        if identity_type != "AGENT_IDENTITY":
            print("⚠️ Warning: Agent Identity is NOT enabled for this engine.")
        else:
            print("✅ Agent Identity is correctly enabled.")

    except Exception as e:
        print(f"❌ Failed to query Vertex AI API: {e}")
        effective_identity = None

    # 2. Verify IAM Permissions
    if effective_identity:
        print("\n🔐 Checking IAM Policy Bindings...")
        cmd = [
            "gcloud",
            "projects",
            "get-iam-policy",
            project_id,
            "--flatten=bindings[].members",
            "--format=value(bindings.role)",
            f"--filter=bindings.members:{effective_identity}",
        ]
        result = run_command(cmd)
        if result.returncode == 0:
            roles = [r for r in result.stdout.strip().split("\n") if r]
            print(f"✅ Found {len(roles)} roles bound to this identity.")

            required_roles = {
                "roles/aiplatform.expressUser",
                "roles/bigquery.jobUser",
                "roles/logging.logWriter",
                "roles/monitoring.metricWriter",
                "roles/cloudtrace.agent",
                "roles/cloudapiregistry.viewer",
                "roles/mcp.toolUser",
            }

            missing = required_roles - set(roles)
            if not missing:
                print("✅ All core SRE roles are present.")
            else:
                print(f"⚠️ Missing core roles: {', '.join(missing)}")
                print("👉 Run: bash deploy/setup_agent_identity_iam.sh to fix.")
        else:
            print(f"❌ Failed to check IAM policy: {result.stderr}")

    print("\n✨ Verification Complete.")


if __name__ == "__main__":
    main()
