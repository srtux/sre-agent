# AutoSRE Deployment Guide

This directory contains the orchestration scripts for deploying the AutoSRE full-stack application.

## Architecture Overview

AutoSRE uses a **dual-mode architecture** that supports both local development and production deployment:

### Development Mode (Local)
```
┌────────────┐     HTTP      ┌────────────────┐     Direct     ┌──────────┐
│  Flutter   │ ────────────► │   FastAPI      │ ─────────────► │ADK Agent │
│  Web App   │               │   Server       │                │ (Local)  │
│  :3000     │ ◄──────────── │   :8001        │ ◄───────────── │          │
└────────────┘               └────────────────┘                └──────────┘

• SRE_AGENT_ID is NOT set
• Agent runs in FastAPI process
• Credentials via ContextVars
• Session storage: SQLite
```

### Production Mode (Deployed)
```
┌────────────┐              ┌────────────────┐    Vertex AI    ┌─────────────┐
│  Browser   │ ───────────► │   Cloud Run    │ ──────────────► │Agent Engine │
│            │              │ (Flutter+Proxy)│ async_stream    │ (ADK Agent) │
│            │ ◄─────────── │                │    _query       │             │
└────────────┘              └────────────────┘ ◄────────────── └─────────────┘
                                   │                                │
                                   │ Session State:                 │
                                   │ _user_access_token ──────────►│
                                   │ _user_project_id ────────────►│
                                                                    ▼
                                                            ┌─────────────┐
                                                            │  GCP APIs   │
                                                            │ (User EUC)  │
                                                            └─────────────┘

• SRE_AGENT_ID IS set (points to deployed Agent Engine)
• Agent runs in Vertex AI Agent Engine
• Credentials via session state
• Session storage: VertexAiSessionService
```

## Deployment Components

| Component | Deployment Target | Purpose |
|-----------|-------------------|---------|
| ADK Agent (`sre_agent`) | Vertex AI Agent Engine | Core reasoning engine, tool execution |
| FastAPI Proxy | Cloud Run | Request routing, EUC extraction, static files |
| Flutter Web App | Cloud Run (static) | User interface |

## Quick Deployment (Recommended)

Deploy the entire stack with a single command:

```bash
uv run poe deploy-all
```

**Options:**
- `--allow-unauthenticated`: Enables unauthenticated access for the Cloud Run frontend.

**What this script does:**
1. **Backend**: Deploys `sre_agent` to Vertex AI Agent Engine via `deploy.py --create`
2. **Capture**: Parses the generated `ReasoningEngine` resource ID
3. **Permissions**: Runs `grant_permissions.py` to grant IAM roles
4. **Frontend**: Deploys Flutter + FastAPI proxy to Cloud Run with `SRE_AGENT_ID` set

## Individual Deployment Scripts

### `deploy.py` - Backend (Agent Engine)

Deploys or updates the `sre_agent` package to Vertex AI Agent Engine.

```bash
# Deploy a new agent or update an existing one (smart deployment)
uv run python deploy/deploy.py --create

# Force creation of a NEW agent resource even if one exists with the same name
uv run python deploy/deploy.py --create --force_new

# Update a specific agent resource by ID
uv run python deploy/deploy.py --create --resource_id <RESOURCE_ID>

# List existing agents
uv run python deploy/deploy.py --list

# Delete an agent
uv run python deploy/deploy.py --delete --resource_id <RESOURCE_ID>
```

**Smart Deployment Behavior:**
The `--create` command is now "smart" by default. It will:
1. Search for an existing Reasoning Engine with the same `display_name` (defaulting to the agent's name).
2. If found, it will **update (patch)** the existing resource. This ensures your query endpoint URL remains unchanged.
3. If not found, it will create a new resource.

**Options:**
- `--create`: Deploy or update an agent.
- `--force_new`: Force creation of a new agent even if one exists with the same name.
- `--resource_id`: Specify a specific Reasoning Engine resource ID to update or delete.
- `--display_name`: Override the display name (used for searching existing agents).
- `--verify`: (Default: True) Verify the agent can be imported locally before deploying.

**Required Environment Variables:**
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `GOOGLE_CLOUD_LOCATION`: Region (e.g., `us-central1`)
- `GOOGLE_CLOUD_STORAGE_BUCKET`: Staging bucket for deployment artifacts

**What Gets Deployed:**
- The `sre_agent` package with all dependencies
- Environment variables for telemetry and EUC handling
- Tracing enabled (`GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`)
- **Deployment Mode**: Sets `SRE_AGENT_DEPLOYMENT_MODE=true` during creation to prevent unpickleable objects (like active model clients or telemetry handlers) from being initialized during pickling.

### `deploy_web.py` - Frontend (Cloud Run)

Deploys the Flutter dashboard and FastAPI proxy to Cloud Run.

```bash
# Deploy with specific agent ID
uv run python deploy/deploy_web.py --agent_id <AGENT_ID>

# Or set SRE_AGENT_ID environment variable
export SRE_AGENT_ID=projects/xxx/locations/xxx/reasoningEngines/xxx
uv run python deploy/deploy_web.py
```
**Options:**
- `--allow-unauthenticated`: Allow public access to Cloud Run. **Note: Authenticated access is the default for security.**

**What Gets Deployed:**
- Flutter Web app (built and served as static files)
- FastAPI proxy that forwards `/agent` requests to Agent Engine
- `SRE_AGENT_ID` environment variable configured

**Key Configuration:**
- Mounts `gemini-api-key` secret from Secret Manager
- Sets `CORS_ALLOW_ALL=true` for Cloud Run domains
- Configures health check at `/health`

### `grant_permissions.py` - IAM Setup

Grants necessary IAM roles to the Cloud Run service account.

```bash
uv run python deploy/grant_permissions.py
```

**Roles Granted:**
| Role | Purpose |
|------|---------|
| `roles/cloudtrace.user` | Read traces |
| `roles/logging.viewer` | Read logs |
| `roles/monitoring.viewer` | Read metrics |
| `roles/bigquery.dataViewer` | Query BigQuery tables |
| `roles/aiplatform.user` | Call Agent Engine |
| `roles/secretmanager.secretAccessor` | Access secrets |
| `roles/datastore.user` | Session persistence |

### 1.1 Establish Agent Identity (Optional but Recommended)

Agent Identity allows the Reasoning Engine to act as its own security principal, enabling background tasks and system-level operations without requiring active user token propagation.

#### 1. Enable Identity during Deployment:
Enable the `--use_agent_identity` flag. This initializes the `vertexai.Client` with the `v1beta1` API version required for identity features.

```bash
uv run python deploy/deploy.py --create --use_agent_identity
```

#### 2. Grant Permissions to the Identity:
The agent requires a broad set of "Viewer" roles to analyze incident signals, plus "Writer" roles for its own telemetry. Use the automation script:

```bash
# Run the setup script
bash deploy/setup_agent_identity_iam.sh \
  --project-id $(gcloud config get-value project) \
  --org-id YOUR_ORG_ID \
  --agent-id YOUR_ENGINE_ID
```

The script grants the following roles to the `principal://agents.global.org-...` URI:
- `roles/aiplatform.expressUser`, `roles/serviceusage.serviceUsageConsumer`
- `roles/cloudtrace.agent`, `roles/cloudtrace.user`
- `roles/logging.viewer`, `roles/logging.logWriter`
- `roles/monitoring.viewer`, `roles/monitoring.metricWriter`
- `roles/bigquery.dataViewer`, `roles/bigquery.jobUser` (for Phase 0 analysis)
- `roles/secretmanager.secretAccessor`, `roles/datastore.user` (for memory)
- `roles/container.viewer`, `roles/container.clusterViewer` (for GKE discovery)

#### 3. Verify the Identity:
You can verify that the identity is active and has correct bindings:

```bash
uv run python deploy/verify_agent_identity.py --agent-id YOUR_ENGINE_ID
```

## End-User Credentials (EUC) Flow

In production, user credentials flow through the system as follows:

```
1. Browser: User signs in with Google OAuth
   ├─► Scopes: email, cloud-platform
   └─► Obtains access_token

2. Flutter Web: Sends request to Cloud Run
   ├─► Authorization: Bearer <access_token>
   └─► X-GCP-Project-ID: <selected_project>

3. Cloud Run (FastAPI Proxy):
   ├─► Middleware extracts token from header
   ├─► Creates AgentEngineClient
   └─► Calls async_stream_query with session containing:
       • _user_access_token: <access_token>
       • _user_project_id: <project_id>

4. Agent Engine:
   ├─► Loads session state
   ├─► Tools call get_credentials_from_tool_context()
   └─► Creates GCP clients with user's credentials

5. GCP APIs:
   └─► Authenticated as the user (not service account)
```

**Key Files:**
- `sre_agent/auth.py`: Credential extraction and validation
- `sre_agent/services/agent_engine_client.py`: Remote Agent Engine client
- `sre_agent/api/routers/agent.py`: Dual-mode `/agent` endpoint

## Prerequisites

### 1. Google Cloud Setup

```bash
# Enable required APIs
gcloud services enable \
  aiplatform.googleapis.com \
  cloudtrace.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  bigquery.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  firestore.googleapis.com

# Create Firestore database (Native Mode)
# If the database doesn't exist:
gcloud firestore databases create --location=us-central1 --type=firestore-native

# If the database already exists in Datastore Mode, switch it to Native Mode:
gcloud firestore databases update --database='(default)' --type=firestore-native
```

### 2. Secrets

```bash
# Gemini API Key (for LLM calls)
echo -n "YOUR_API_KEY" | gcloud secrets create gemini-api-key --data-file=-

# Google OAuth Client ID (for frontend)
echo -n "YOUR_CLIENT_ID" | gcloud secrets create google-client-id --data-file=-

# SRE Agent Encryption Key (for securing session tokens)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
echo -n "YOUR_ENCRYPTION_KEY" | gcloud secrets create sre-agent-encryption-key --data-file=-

# IMPORTANT: You MUST also add this key to your local .env file.
# The backend (Agent Engine) pulls this key from your local environment at deployment time.
# The frontend (Cloud Run) pulls this key from Secret Manager at runtime.
# If they don't match, user tokens cannot be decrypted.
```

### 3. OAuth Configuration

1. Go to **Google Cloud Console > APIs & Credentials**
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized JavaScript origins:
   - `http://localhost:3000` (development)
   - `https://your-cloud-run-url.run.app` (production)

### 4. Environment Configuration

Create `.env` file:

```bash
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_CLOUD_STORAGE_BUCKET=your-staging-bucket
GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com
```

## Verification After Deployment

1. Visit the Cloud Run URL from deployment output

2. **If OAuth error** ("Access blocked: Authorization Error"):
   - Go to **GCP Console > Credentials**
   - Find your OAuth 2.0 Client ID
   - Add Cloud Run URL to **Authorized JavaScript Origins**
   - Wait up to 5 minutes

3. Sign in with Google

4. Test the agent:
   ```
   "List the GCP projects I have access to"
   ```

5. Verify EUC is working:
   - You should only see projects your Google account has access to
   - Not projects accessible by the service account

## Troubleshooting

### Agent Engine Connection Failed

```bash
# Check if SRE_AGENT_ID is set correctly
gcloud run services describe sre-agent --format='value(spec.template.spec.containers[0].env)'

# Verify agent exists
uv run python deploy/deploy.py --list
```

### EUC Not Working (Service Account Used Instead)

```bash
# Enable strict EUC enforcement
gcloud run services update sre-agent --set-env-vars STRICT_EUC_ENFORCEMENT=true

# Check auth debug endpoint
curl -H "Authorization: Bearer <token>" https://your-url/api/auth/info
```

### Firestore 400: API not available for Datastore Mode
**Symptom**: `Firestore get error: 400 The Cloud Firestore API is not available for Firestore in Datastore Mode database`

**Cause**: The `(default)` database in your project was initialized in Datastore Mode, but the agent requires Firestore Native Mode.

**Fix**:
1. Convert the database to Native Mode:
   ```bash
   gcloud firestore databases update --database='(default)' --type=firestore-native
   ```
2. Ensure permissions are granted to the Reasoning Engine service account:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:service-YOUR_PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
     --role="roles/datastore.user" \
     --condition=None
   ```

### Session State Issues

```bash
# Check session service type in logs
gcloud logging read "resource.type=cloud_run_revision AND textPayload:SessionService"
```

## Evaluations

Run agent evaluations to benchmark performance:

```bash
uv run poe eval
```

This loads test cases from `eval/` and reports success/failure rates.

## GKE Deployment (Kubernetes)

AutoSRE can be deployed to GKE using the provided Kubernetes manifests and orchestration script. This runs the **Unified Container** (Frontend + Proxy Backend) in your cluster.

### 1. Prerequisites
- A running GKE cluster.
- `kubectl` and `gcloud` configured.
- Docker image built and pushed to a registry (GCR/AR). Use `cloudbuild.yaml` or `gcloud builds submit`.

### 2. Deploy via Script
```bash
uv run poe deploy-gke --cluster <CLUSTER_NAME> --region <REGION>
```

**Options:**
- `--cluster`: Name of your GKE cluster.
- `--zone` or `--region`: Location of your cluster.
- `--agent-id`: (Optional) Connect to a deployed Vertex Agent Engine resource. If omitted, the agent runs in **Local Mode** inside the pod.

### 3. Manual Deployment
Manifests are located in `deploy/k8s/`:
- `deployment.yaml`: Deployment spec with ConfigMap/Secret references.
- `service.yaml`: LoadBalancer service to expose the dashboard.

## Cloud Run Deployment (Unified)

While `deploy-all` is the recommended way to use Vertex AI Agent Engine, you can also run the **entire agent stack** inside a single Cloud Run service (Local Mode).

### 1. Build and Deploy
```bash
# Build and push image
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/autosre:latest

# Deploy to Cloud Run without SRE_AGENT_ID (Default to Local Mode)
uv run python deploy/deploy_web.py --service-name autosre-unified
```

### 2. Why run on Cloud Run/GKE vs Agent Engine?
- **Agent Engine**: Best for background tasks, production stability, and native Vertex AI integrations.
- **GKE/Cloud Run (Local Mode)**: Lower latency for chat interactions, easier to debug, and simplified networking for local tools.

## Related Documentation

- [Main README](../README.md): Architecture overview
- [CLAUDE.md](../CLAUDE.md): Development guide for AI assistants
- [Auth Debugging](../docs/debugging_telemetry_and_auth.md): Troubleshooting EUC issues
