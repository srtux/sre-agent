import argparse
import subprocess
import sys


def run_command(cmd, exit_on_fail=True):
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Command failed: {result.stderr}")
        if exit_on_fail:
            sys.exit(1)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Grant IAM permissions to Cloud Run Service Account"
    )
    parser.add_argument("--project-id", help="GCP Project ID", required=True)
    parser.add_argument(
        "--service-account",
        help="Service Account Email (optional, defaults to Compute Engine default)",
    )
    args = parser.parse_args()

    project_id = args.project_id

    # 1. Determine Service Account
    sa_email = args.service_account
    if not sa_email:
        print("🔍 Finding default Compute Engine service account...")
        project_number = run_command(
            [
                "gcloud",
                "projects",
                "describe",
                project_id,
                "--format=value(projectNumber)",
            ]
        )
        if not project_number:
            print("❌ Could not get project number.")
            sys.exit(1)

        sa_email = f"{project_number}-compute@developer.gserviceaccount.com"
        print(f"✅ Found Service Account: {sa_email}")

    # 2. List of Roles to Grant
    roles = [
        "roles/cloudtrace.user",  # Read traces
        "roles/logging.viewer",  # Read logs
        "roles/monitoring.viewer",  # Read metrics
        "roles/bigquery.dataViewer",  # Query BigQuery
        "roles/aiplatform.user",  # Access Vertex AI Agent Engine
        "roles/secretmanager.secretAccessor",  # Access keys
    ]

    print("\n🔐 Granting IAM Roles...")
    for role in roles:
        print(f"   Granting {role}...")
        run_command(
            [
                "gcloud",
                "projects",
                "add-iam-policy-binding",
                project_id,
                f"--member=serviceAccount:{sa_email}",
                f"--role={role}",
                "--condition=None",
            ],
            exit_on_fail=False,
        )

    print(f"\n✅ Successfully granted permissions to {sa_email}")
    print("🚀 You can now deploy the Unified Container.")


if __name__ == "__main__":
    main()
