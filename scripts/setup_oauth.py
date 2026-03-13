#!/usr/bin/env python3
"""setup_oauth.py - Assist and automate OAuth Client ID setup for AutoSRE.

This script:
1. Detects the GCP Project and Cloud Run URL.
2. Guides the user to create/configure a Client ID in the Google Cloud Console.
3. Automatically updates Secret Manager and local .env with the new Client ID.
"""

import os
import subprocess
import sys


def run_cmd(cmd, check=True, capture_output=True):
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, capture_output=capture_output, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if capture_output:
            print(f"Error running command: {e.stderr}")
        raise e


def main():
    """Main execution function for setup."""
    print("🛠️  AutoSRE OAuth Setup Helper\n")

    # 1. Resolve Project ID
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        # Try finding in .env
        if os.path.exists(".env"):
            with open(".env") as f:
                for line in f:
                    if line.startswith("GOOGLE_CLOUD_PROJECT="):
                        project_id = line.split("=")[1].strip()
                        break
                    if line.startswith("PROJECT_ID="):
                        project_id = line.split("=")[1].strip()

    if not project_id:
        try:
            project_id = run_cmd("gcloud config get-value project")
        except Exception:
            pass

    if not project_id:
        print("❌ Error: Could not determine GCP Project ID.")
        print("Please set GCP_PROJECT_ID or run 'gcloud config set project [PROJECT]'")
        sys.exit(1)

    print(f"📌 Project ID: {project_id}")

    # 2. Get Cloud Run URL
    print("🔍 Fetching Cloud Run service details...")
    service_name = "autosre"  # Default name from deploy_web.py
    url = ""
    try:
        url = run_cmd(
            f"gcloud run services describe {service_name} --project={project_id} --format='value(status.url)' --quiet"
        )
    except Exception:
        # Try listing if describe fails (maybe service name is different)
        try:
            output = run_cmd(
                f"gcloud run services list --project={project_id} --format='value(status.url)' --quiet"
            )
            urls = output.split()
            for u in urls:
                if "autosre" in u:
                    url = u
                    break
            if not url and urls:
                url = urls[0]  # Fallback to first one
        except Exception:
            pass

    if not url:
        print("\n⚠️  Could not automatically find your Cloud Run URL.")
        url = input("Please enter your Cloud Run URL (e.g., https://...): ").strip()

    # Normalize URL (remove trailing slash)
    if url.endswith("/"):
        url = url[:-1]

    print(f"🌐 Cloud Run URL: {url}")

    # 3. Print Instructions
    print("\n--- 📝 ACTION REQUIRED IN GOOGLE CLOUD CONSOLE ---")
    print(
        "Due to security policies, Authorized JavaScript origins must be set via the Console."
    )
    print("\n1. Open the Credentials page in your browser:")
    print(
        f"   👉 https://console.cloud.google.com/apis/credentials?project={project_id}"
    )
    print("\n2. Click 'Create Credentials' -> 'OAuth client ID'")
    print("3. Application type: 'Web application'")
    print("4. Name: AutoSRE Client")
    print("\n5. 📍 Under 'Authorized JavaScript origins', add this exact URL:")
    print(f"      {url}")
    print("\n6. Click 'Create'")
    print("7. Copy the NEW Client ID provided.")
    print("----------------------------------------------------\n")

    # 4. Prompt for New Client ID
    new_id = input("🔑 Enter your NEW OAuth Client ID: ").strip()
    if not new_id:
        print("❌ Setup cancelled. No Client ID provided.")
        sys.exit(1)

    # 5. Update Secret Manager
    print("\n🔒 Updating Secret Manager...")
    secret_name = "google-client-id"  # pragma: allowlist secret
    try:
        # Check if secret exists
        run_cmd(f"gcloud secrets describe {secret_name} --project={project_id}")
        # Add new version
        run_cmd(
            f"echo -n '{new_id}' | gcloud secrets versions add {secret_name} --data-file=- --project={project_id}"
        )
        print(f"✅ Secret Manager '{secret_name}' updated to new version.")
    except Exception as e:
        print(f"⚠️  Could not update Secret Manager automatically: {e}")
        print(f"Please update the secret '{secret_name}' manually with the new value.")

    # 6. Update .env
    if os.path.exists(".env"):
        print("\n✏️  Updating local .env file...")
        updated = False
        lines = []
        with open(".env") as f:
            for line in f:
                if line.startswith("GOOGLE_CLIENT_ID="):
                    lines.append(f"GOOGLE_CLIENT_ID={new_id}\n")
                    updated = True
                else:
                    lines.append(line)

        if not updated:
            # Append if not found
            lines.append(f"GOOGLE_CLIENT_ID={new_id}\n")

        with open(".env", "w") as f:
            f.writelines(lines)
        print("✅ Local .env updated.")

    print("\n🎉 OAuth configuration update prepared!")
    print("To apply this to your deployment, run your deployment script")
    print("or wait for the next rollout.")


if __name__ == "__main__":
    main()
