# Toolbox MCP Server

This directory contains the configuration and deployment scripts for running a **Google GenAI Toolbox** based MCP server on Google Cloud Run.

It exposes Google Cloud tools (like BigQuery) via the Model Context Protocol (MCP), allowing agents to securely interact with your data.

## Architecture

- **Image**: Uses the official `us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest` image.
- **Platform**: Google Cloud Run (Serverless).
- **Auth**: Service Account (`toolbox-sa`) with strictly scoped permissions (`roles/bigquery.jobUser`, `roles/bigquery.dataViewer`).
- **Configuration**: `config.yaml` mounted as a secret.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and authenticated.
- A Google Cloud Project with billing enabled.
- `run.googleapis.com` and `secretmanager.googleapis.com` APIs enabled.

## Configuration

The `config.yaml` file defines which tools are enabled.

```yaml
sources:
  bigquery:
    kind: bigquery
    project: ${GOOGLE_CLOUD_PROJECT}
    # useClientOAuth: true # Uncomment to use the caller's credentials instead of the Service Account
```

### Authentication Modes
- **Service Account (Default)**: The server uses the `toolbox-sa` identity. Simple and secure for internal tools. We verified this setup works.
- **Client OAuth (`useClientOAuth: true`)**: The server uses the credentials of the user/agent calling the tool. Useful for auditing or row-level security based on the specific user. Requires passing the user's Access Token.

## Deployment

The `deploy.sh` script automates the entire process:
1.  Creates a dedicated Service Account (`toolbox-sa`).
2.  Grants necessary IAM permissions (Secret Accessor, BigQuery User).
3.  Uploads `config.yaml` to Secret Manager.
4.  Deploys the Toolbox container to Cloud Run with correct arguments.

```bash
./deploy.sh
```

### Script details
The script ensures permissions are applied non-interactively and uses your active `gcloud` project by default.

## Usage

After deployment, the script will output the Service URL.

1.  Copy the URL.
2.  Set it in your agent's `.env` file:
    ```env
    TOOLBOX_MCP_URL=https://toolbox-mcp-xyz-uc.a.run.app
    ```

## Troubleshooting

If deployment fails with "Container failed to start", check Cloud Run logs for config parsing errors. Ensure `config.yaml` uses the `sources` mapping format, not a list.
