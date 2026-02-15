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
1. **Discovery**: Searches for an existing Agent Engine resource by display name (`sre_agent`).
2. **Parallel (existing agent)**: If found, launches backend patch and frontend deployment in parallel using threads. Logs are prefixed with `[BACKEND]` and `[FRONTEND]`.
3. **Sequential (new agent)**: If no agent exists, deploys backend first, captures the resource name, then deploys the frontend.
4. **Permissions**: `deploy_web.py` automatically invokes `grant_permissions.py` to grant IAM roles.

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

**Concurrent Update Handling:**
If a Vertex AI update is already in progress, `deploy.py` retries up to 12 times with a 60-second interval (total ~12 minutes) before failing.

**Flags:**

| Flag | Description |
|------|-------------|
| `--create` | Deploy or update an agent |
| `--force_new` | Force creation of a new agent even if one exists with the same name |
| `--resource_id` | Specify a specific Reasoning Engine resource ID to update or delete |
| `--display_name` | Override the display name (used for searching existing agents) |
| `--description` | Override the description for the agent |
| `--verify` | (Default: True) Verify the agent can be imported locally before deploying |
| `--service_account` | Service account for the agent (not used with Agent Identity) |
| `--min_instances` | Minimum instances (default: 1) |
| `--max_instances` | Maximum instances |
| `--use_agent_identity` | Enable Agent Identity for the Reasoning Engine (uses v1beta1 API) |

**Required Environment Variables:**
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `GOOGLE_CLOUD_LOCATION`: Region (e.g., `us-central1`)
- `GOOGLE_CLOUD_STORAGE_BUCKET`: Staging bucket for deployment artifacts

**What Gets Deployed:**
- The `sre_agent` package with all dependencies (parsed from `pyproject.toml`, merged with pinned deployment versions)
- Dependencies exclude server-specific packages (`fastapi`, `uvicorn`, `starlette`, etc.) since the Agent Engine does not serve HTTP
- Environment variables for telemetry and EUC handling (see below)
- Tracing enabled (`GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`)
- **Deployment Mode**: Sets `SRE_AGENT_DEPLOYMENT_MODE=true` during creation to prevent unpickleable objects (like active model clients or telemetry handlers) from being initialized during pickling.

**Environment Variables Propagated to Agent Engine:**

The following environment variables are **always set** on the deployed agent:

| Variable | Value / Source |
|----------|----------------|
| `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY` | `true` |
| `ADK_OTEL_TO_CLOUD` | `true` |
| `OTEL_SERVICE_NAME` | `sre-agent` |
| `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED` | `true` |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | `true` |
| `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS` | `false` |
| `RUNNING_IN_AGENT_ENGINE` | `true` |
| `LOG_FORMAT` | `JSON` |
| `LOG_LEVEL` | From local env or `INFO` |
| `STRICT_EUC_ENFORCEMENT` | From local env or `false` |
| `SRE_AGENT_ENFORCE_POLICY` | From local env or `true` |
| `SRE_AGENT_ENCRYPTION_KEY` | From local env (required for token encryption) |
| `USE_ARIZE` | From local env or `false` |
| `GCP_LOCATION` | From `GOOGLE_CLOUD_LOCATION` |
| `AGENT_ENGINE_LOCATION` | From `AGENT_ENGINE_LOCATION` env var |
| `GCP_PROJECT_ID` | From resolved project ID |

The following are **conditionally propagated** from the local environment if set:

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CUSTOM_SEARCH_API_KEY` | API key for Google Custom Search (research tools) |
| `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` | Programmable Search Engine ID (research tools) |
| `GITHUB_TOKEN` | GitHub personal access token (GitHub integration tools) |
| `GITHUB_REPO` | Default GitHub repository (e.g., `org/repo`) |
| `SRE_AGENT_CONTEXT_CACHE_TTL` | Context cache TTL in seconds |
| `SRE_AGENT_COUNCIL_ORCHESTRATOR` | Enable Council of Experts architecture |
| `SRE_AGENT_SLIM_TOOLS` | Reduce root agent tools to ~20 |
| `SRE_AGENT_CIRCUIT_BREAKER` | Enable circuit breaker pattern |

> **Important**: `GOOGLE_CUSTOM_SEARCH_API_KEY`, `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`, `GITHUB_TOKEN`, and `GITHUB_REPO` must be set in your local `.env` file (or shell environment) at deploy time for them to be propagated to the Agent Engine. They are baked into the environment at deployment, not fetched from Secret Manager at runtime.

### `deploy_web.py` - Frontend (Cloud Run)

Deploys the Flutter dashboard and FastAPI proxy to Cloud Run.

```bash
# Deploy with specific agent ID
uv run python deploy/deploy_web.py --agent-id <AGENT_ID>

# Or set SRE_AGENT_ID environment variable
export SRE_AGENT_ID=projects/xxx/locations/xxx/reasoningEngines/xxx
uv run python deploy/deploy_web.py

# Deploy with a custom service name
uv run python deploy/deploy_web.py --service-name autosre-staging

# Deploy a pre-built Docker image (skip build)
uv run python deploy/deploy_web.py --image gcr.io/my-project/autosre:v1.2
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--agent-url` | URL of the SRE Agent backend (e.g., from `adk web`) |
| `--agent-id` | Vertex Reasoning Engine resource ID |
| `--project-id` | GCP Project ID (falls back to `GOOGLE_CLOUD_PROJECT` or `gcloud config`) |
| `--region` | GCP Region (default: `us-central1`) |
| `--service-name` | Cloud Run service name (default: `autosre`) |
| `--image` | Pre-built Docker image to deploy (skips Cloud Build) |
| `--allow-unauthenticated` | Allow public access to Cloud Run. **Authenticated access is the default for security.** |

**Resource Requirements:**
- **Memory**: 16 GiB
- **CPU**: 4 vCPUs
- **Timeout**: 300 seconds

**What Gets Deployed:**
- Flutter Web app (built and served as static files)
- FastAPI proxy that forwards `/agent` requests to Agent Engine
- `SRE_AGENT_ID` and `SRE_AGENT_URL` environment variables configured (if provided)
- Automatic IAM permission grants via `grant_permissions.py`

**Secret Manager Mounts (Cloud Run):**

The following secrets are mounted as environment variables from Google Cloud Secret Manager:

| Cloud Run Env Var | Secret Manager Secret | Purpose |
|-------------------|-----------------------|---------|
| `GOOGLE_API_KEY` | `gemini-api-key:latest` | Gemini API key (primary) |
| `GEMINI_API_KEY` | `gemini-api-key:latest` | Gemini API key (alias) |
| `GOOGLE_GENERATIVE_AI_API_KEY` | `gemini-api-key:latest` | Gemini API key (legacy alias) |
| `GOOGLE_CLIENT_ID` | `google-client-id:latest` | Google OAuth Client ID for frontend |
| `SRE_AGENT_ENCRYPTION_KEY` | `sre-agent-encryption-key:latest` | Fernet key for encrypting session tokens |

**Environment Variables Set on Cloud Run:**

| Variable | Value |
|----------|-------|
| `GCP_PROJECT_ID` | Resolved project ID |
| `GCP_REGION` | Deployment region |
| `AGENT_ENGINE_LOCATION` | Same as region |
| `GOOGLE_CLOUD_LOCATION` | From local env or region |
| `STRICT_EUC_ENFORCEMENT` | From local env or `true` |
| `LOG_FORMAT` | `JSON` |
| `LOG_LEVEL` | From local env or `INFO` |
| `WEB_CONCURRENCY` | `2` |
| `USE_ARIZE` | `false` |
| `SRE_AGENT_URL` | Agent URL (if provided) |
| `SRE_AGENT_ID` | Agent resource ID (if provided) |

**Health Check:**
- Configures health check at `/health` (built into FastAPI server)

### `grant_permissions.py` - IAM Setup

Grants necessary IAM roles to the Cloud Run / Compute Engine default service account.

```bash
uv run python deploy/grant_permissions.py --project-id YOUR_PROJECT_ID

# Or with a custom service account
uv run python deploy/grant_permissions.py --project-id YOUR_PROJECT_ID --service-account my-sa@project.iam.gserviceaccount.com
```

> **Note**: `deploy_web.py` automatically invokes `grant_permissions.py` before deploying. You typically do not need to run this manually.

**Roles Granted to Service Account:**

| Role | Purpose |
|------|---------|
| `roles/cloudtrace.agent` | Write traces (OTel) |
| `roles/cloudtrace.user` | Read traces |
| `roles/telemetry.writer` | Write telemetry via OTLP API (ADK native) |
| `roles/logging.viewer` | Read logs |
| `roles/logging.logWriter` | Write logs |
| `roles/monitoring.viewer` | Read metrics |
| `roles/monitoring.metricWriter` | Write metrics |
| `roles/bigquery.dataViewer` | Query BigQuery tables |
| `roles/aiplatform.user` | Access Vertex AI Agent Engine |
| `roles/secretmanager.secretAccessor` | Access secrets |
| `roles/datastore.user` | Firestore document access (sessions) |

**Additionally**, the script grants `roles/iam.serviceAccountUser` to the Vertex AI service agents:
- `service-<PROJECT_NUMBER>@gcp-sa-aiplatform.iam.gserviceaccount.com`
- `service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`

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

| Role | Purpose |
|------|---------|
| `roles/aiplatform.expressUser` | Vertex AI Express access |
| `roles/serviceusage.serviceUsageConsumer` | Service usage |
| `roles/cloudtrace.agent` | Write traces |
| `roles/cloudtrace.user` | Read traces |
| `roles/logging.viewer` | Read logs |
| `roles/logging.logWriter` | Write logs |
| `roles/monitoring.viewer` | Read metrics |
| `roles/monitoring.metricWriter` | Write metrics |
| `roles/bigquery.dataViewer` | Read BigQuery data |
| `roles/bigquery.jobUser` | Run BigQuery jobs |
| `roles/secretmanager.secretAccessor` | Access secrets |
| `roles/datastore.user` | Firestore/Datastore access (memory) |
| `roles/container.viewer` | View GKE resources |
| `roles/container.clusterViewer` | View GKE clusters |
| `roles/cloudapiregistry.viewer` | View API registry |
| `roles/mcp.toolUser` | Use MCP tools |

#### 3. Verify the Identity:
You can verify that the identity is active and has correct bindings:

```bash
uv run python deploy/verify_agent_identity.py --agent-id YOUR_ENGINE_ID
```

## End-User Credentials (EUC) Flow

In production, user credentials flow through the system as follows:

```
1. Browser: User signs in with Google OAuth
   ├── Scopes: email, cloud-platform
   └── Obtains access_token

2. Flutter Web: Sends request to Cloud Run
   ├── Authorization: Bearer <access_token>
   └── X-GCP-Project-ID: <selected_project>

3. Cloud Run (FastAPI Proxy):
   ├── Middleware extracts token from header
   ├── Creates AgentEngineClient
   └── Calls async_stream_query with session containing:
       • _user_access_token: <access_token>
       • _user_project_id: <project_id>

4. Agent Engine:
   ├── Loads session state
   ├── Tools call get_credentials_from_tool_context()
   └── Creates GCP clients with user's credentials

5. GCP APIs:
   └── Authenticated as the user (not service account)
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
  firestore.googleapis.com \
  container.googleapis.com

# Create Firestore database (Native Mode)
# If the database doesn't exist:
gcloud firestore databases create --location=us-central1 --type=firestore-native

# If the database already exists in Datastore Mode, switch it to Native Mode:
gcloud firestore databases update --database='(default)' --type=firestore-native
```

### 2. Secrets

The following secrets must be created in Google Cloud Secret Manager:

```bash
# Gemini API Key (for LLM calls)
echo -n "YOUR_API_KEY" | gcloud secrets create gemini-api-key --data-file=-

# Google OAuth Client ID (for frontend login)
echo -n "YOUR_CLIENT_ID" | gcloud secrets create google-client-id --data-file=-

# SRE Agent Encryption Key (for securing session tokens)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
echo -n "YOUR_ENCRYPTION_KEY" | gcloud secrets create sre-agent-encryption-key --data-file=-
```

> **IMPORTANT**: The encryption key must ALSO be set in your local `.env` file. The backend (Agent Engine) pulls this key from your local environment at deployment time. The frontend (Cloud Run) pulls this key from Secret Manager at runtime. If they do not match, user tokens cannot be decrypted.

**Additional secrets for CI/CD pipeline** (required if using Cloud Build):

```bash
# Google Custom Search API Key (for research tools)
echo -n "YOUR_SEARCH_KEY" | gcloud secrets create google-custom-search-api-key --data-file=-

# GitHub Token (for GitHub integration tools)
echo -n "YOUR_GITHUB_TOKEN" | gcloud secrets create github-token --data-file=-

# (Optional) Eval Project ID - use a different project for evaluations
echo -n "YOUR_EVAL_PROJECT" | gcloud secrets create eval-project-id --data-file=-
```

> **Note**: For local deployments (not CI/CD), `GOOGLE_CUSTOM_SEARCH_API_KEY`, `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`, `GITHUB_TOKEN`, and `GITHUB_REPO` are propagated from your local environment to the Agent Engine by `deploy.py`. Set them in your `.env` file.

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
SRE_AGENT_ENCRYPTION_KEY=your-fernet-key

# Optional: Research and GitHub integration
GOOGLE_CUSTOM_SEARCH_API_KEY=your-search-api-key
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your-search-engine-id
GITHUB_TOKEN=your-github-token
GITHUB_REPO=your-org/your-repo

# Optional: Agent features
SRE_AGENT_COUNCIL_ORCHESTRATOR=true
SRE_AGENT_SLIM_TOOLS=true
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
gcloud run services describe autosre --format='value(spec.template.spec.containers[0].env)'

# Verify agent exists
uv run python deploy/deploy.py --list
```

### EUC Not Working (Service Account Used Instead)

```bash
# Enable strict EUC enforcement
gcloud run services update autosre --set-env-vars STRICT_EUC_ENFORCEMENT=true

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

### Concurrent Update Errors
If `deploy.py` reports "Concurrent update detected", it means another deployment is in progress. The script retries automatically (up to 12 times at 60-second intervals). Wait for the existing deployment to complete or check the Vertex AI console.

## Evaluations

Run agent evaluations to benchmark performance:

```bash
uv run poe eval
```

This loads test cases from `eval/` and reports success/failure rates.

## Docker Image

The project uses a **multi-stage Dockerfile** located at the project root (`Dockerfile`). A backup copy exists at `deploy/Dockerfile.unified`.

**Build stages:**
1. **Builder** (debian:bookworm-slim): Installs Flutter SDK, builds the Flutter web app
2. **Production** (python:3.11-slim): Installs Python backend with `uv`, copies built Flutter web assets

**Build args:**

| Arg | Purpose |
|-----|---------|
| `BUILD_SHA` | Git commit SHA (injected by Cloud Build) |
| `BUILD_TIMESTAMP` | Build timestamp |

**Runtime environment:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `8080` | Server listen port |
| `HOSTNAME` | `0.0.0.0` | Server bind address |
| `SRE_AGENT_URL` | `http://127.0.0.1:8001` | Agent backend URL |
| `PYTHONUNBUFFERED` | `1` | Unbuffered Python output |

**Server configuration:**
- The `server.py` entry point runs uvicorn with workers matching `WEB_CONCURRENCY` (default: 4)
- Each worker process uses approximately 250-350 MB with the full GCP SDK stack
- Cloud Run deployment allocates 4 CPUs / 16 GiB -- 4 workers fits comfortably

## GKE Deployment (Kubernetes)

AutoSRE can be deployed to GKE using the provided Kubernetes manifests and orchestration script. This runs the **Unified Container** (Frontend + Proxy Backend) in your cluster.

### 1. Prerequisites
- A running GKE cluster
- `kubectl` and `gcloud` CLI configured
- Docker image built and pushed to a registry (GCR/AR). Use `cloudbuild.yaml` or `gcloud builds submit`.

### 2. Deploy via Script
```bash
uv run python deploy/deploy_gke.py --cluster <CLUSTER_NAME> --region <REGION>
```

Or use the poethepoet task:
```bash
uv run poe deploy-gke --cluster <CLUSTER_NAME> --region <REGION>
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--cluster` | Name of your GKE cluster (required) |
| `--zone` | Zone of your cluster (provide either `--zone` or `--region`) |
| `--region` | Region of your cluster (provide either `--zone` or `--region`) |
| `--project-id` | GCP project ID (falls back to `GOOGLE_CLOUD_PROJECT`) |
| `--agent-id` | Connect to a deployed Vertex Agent Engine resource. If omitted, the agent runs in **Local Mode** inside the pod. |

**What the script does:**
1. Fetches GKE cluster credentials via `gcloud container clusters get-credentials`
2. Creates a Kubernetes ConfigMap (`autosre-config`) with `project_id` and `agent_id`
3. Creates a Kubernetes Secret (`autosre-secrets`) with `gemini_api_key`, `encryption_key`, and `google_client_id` (sourced from local env vars `GEMINI_API_KEY`/`GOOGLE_API_KEY`, `SRE_AGENT_ENCRYPTION_KEY`, `GOOGLE_CLIENT_ID`)
4. Applies deployment and service manifests from `deploy/k8s/`

### 3. Kubernetes Manifests

Manifests are located in `deploy/k8s/`:

**`deployment.yaml`:**
- Deployment spec with 1 replica
- Container image: `gcr.io/PROJECT_ID/autosre:latest` (replaced at deploy time)
- Container port: 8080
- Environment from ConfigMap (`autosre-config`): `GCP_PROJECT_ID`, `SRE_AGENT_ID`
- Environment from Secret (`autosre-secrets`): `GEMINI_API_KEY`, `SRE_AGENT_ENCRYPTION_KEY`, `GOOGLE_CLIENT_ID`

**`service.yaml`:**
- LoadBalancer service exposing port 80 -> container port 8080

### 4. Manual Deployment
```bash
# Build and push image
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/autosre:latest

# Create ConfigMap
kubectl create configmap autosre-config \
  --from-literal=project_id=$GOOGLE_CLOUD_PROJECT \
  --from-literal=agent_id=$SRE_AGENT_ID \
  --dry-run=client -o yaml | kubectl apply -f -

# Create Secret
kubectl create secret generic autosre-secrets \
  --from-literal=gemini_api_key=$GEMINI_API_KEY \
  --from-literal=encryption_key=$SRE_AGENT_ENCRYPTION_KEY \
  --from-literal=google_client_id=$GOOGLE_CLIENT_ID \
  --dry-run=client -o yaml | kubectl apply -f -

# Apply manifests (update image in deployment.yaml first)
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml

# Check status
kubectl get service autosre
```

## Cloud Run Deployment (Unified)

While `deploy-all` is the recommended way to use Vertex AI Agent Engine, you can also run the **entire agent stack** inside a single Cloud Run service (Local Mode).

### 1. Build and Deploy
```bash
# Build and push image
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/autosre:latest

# Deploy to Cloud Run without SRE_AGENT_ID (defaults to Local Mode)
uv run python deploy/deploy_web.py --service-name autosre-unified
```

### 2. Why run on Cloud Run/GKE vs Agent Engine?
- **Agent Engine**: Best for background tasks, production stability, and native Vertex AI integrations.
- **GKE/Cloud Run (Local Mode)**: Lower latency for chat interactions, easier to debug, and simplified networking for local tools.

## CI/CD Pipeline

See [docs/infrastructure/DEPLOYMENT.md](../infrastructure/DEPLOYMENT.md) for the full CI/CD pipeline documentation.

## Related Documentation

- [Main README](../../README.md): Architecture overview
- [Infrastructure Deployment](../infrastructure/DEPLOYMENT.md): CI/CD pipeline details
- [CLAUDE.md](../../CLAUDE.md): Development guide for AI assistants
- [Configuration Reference](../reference/configuration.md): Full environment variable reference
