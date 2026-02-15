# CI/CD Pipeline

The project uses **Google Cloud Build** for continuous integration and deployment, defined in `cloudbuild.yaml`.

## Pipeline Overview

The pipeline is a 7-stage process with two parallel tracks that converge before the frontend deployment. After deployment, an optional evaluation stage runs as an asynchronous quality gate.

```
Track A (slow):                Track B (fast):
  deploy-backend                 fetch-resource-id
        |                              |
        |                        build-image
        |                              |
        |                         push-image
        |                              |
        +----------+---+--------------+
                   |
             deploy-frontend
                   |
              run-evals (non-blocking)
```

## Pipeline Stages

### Stage 1: Deploy Agent Engine Backend (`deploy-backend`)
- **Image**: `gcr.io/google.com/cloudsdktool/cloud-sdk`
- **Runs in parallel**: Starts immediately (`waitFor: ['-']`)
- **What it does**:
  1. Installs `uv` and Python 3.12.
  2. Runs `uv sync` to install all dependencies.
  3. Executes `uv run python deploy/deploy.py --create` to deploy or update the Agent Engine backend.
  4. The deploy script checks for an existing agent named `sre_agent` and patches it if found, or creates a new one.
- **Secrets used**: `SRE_AGENT_ENCRYPTION_KEY`, `GOOGLE_CUSTOM_SEARCH_API_KEY`, `GITHUB_TOKEN`
- **Key env vars**: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_CLOUD_STORAGE_BUCKET`, `SRE_AGENT_COUNCIL_ORCHESTRATOR`, `SRE_AGENT_SLIM_TOOLS`

### Stage 2: Fetch Agent Engine Resource ID (`fetch-resource-id`)
- **Image**: `gcr.io/google.com/cloudsdktool/cloud-sdk`
- **Runs in parallel**: Starts immediately (`waitFor: ['-']`)
- **What it does**:
  1. Installs `jq`.
  2. Queries the Vertex AI REST API directly (no Python environment needed) to look up the stable Agent Engine resource name by display name (`sre_agent`).
  3. Writes the resource name to `backend_resource_name.txt` for downstream stages.
  4. Fails the build if no agent named `sre_agent` is found (requires initial manual deployment).

### Stage 3: Build Unified Docker Image (`build-image`)
- **Image**: `gcr.io/cloud-builders/docker`
- **Waits for**: `fetch-resource-id`
- **What it does**:
  1. Reads the Agent Engine resource name from `backend_resource_name.txt`.
  2. Constructs the Agent Engine query URL from the resource name.
  3. Builds the Docker image with build args:
     - `SRE_AGENT_URL`: The Agent Engine query endpoint.
     - `SRE_AGENT_ID`: The full resource name.
     - `BUILD_SHA`: The short commit SHA for traceability.
     - `BUILD_TIMESTAMP`: UTC build timestamp.

### Stage 4: Push Image (`push-image`)
- **Image**: `gcr.io/cloud-builders/docker`
- **Waits for**: `build-image`
- **What it does**: Pushes `gcr.io/$PROJECT_ID/autosre:latest` to Google Container Registry.

### Stage 5: Deploy to Cloud Run (`deploy-frontend`)
- **Image**: `gcr.io/google.com/cloudsdktool/cloud-sdk`
- **Waits for**: `push-image`
- **What it does**:
  1. Reads the Agent Engine resource name from `backend_resource_name.txt`.
  2. Deploys the unified image to Cloud Run as the `autosre` service with:
     - **Memory**: 16Gi
     - **CPU**: 4
     - **Access**: `--allow-unauthenticated`
     - **Environment variables**: `SRE_AGENT_URL`, `SRE_AGENT_ID`, `GCP_PROJECT_ID`, telemetry configuration (OTEL, ADK), logging, and policy settings.
     - **Secrets** (mounted from Secret Manager): `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `SRE_AGENT_ENCRYPTION_KEY`.

### Stage 6: Run Evaluation Suite (`run-evals`)
- **Image**: `gcr.io/google.com/cloudsdktool/cloud-sdk`
- **Waits for**: `deploy-frontend` (runs after deployment to avoid blocking the release)
- **Allowed to fail**: `allowFailure: true` (non-blocking quality gate)
- **What it does**:
  1. Resolves the GCP project ID: uses `EVAL_PROJECT_ID` secret if available, otherwise falls back to the build project (`$PROJECT_ID`).
  2. Installs `uv` and Python 3.12, runs `uv sync`.
  3. Executes `uv run poe eval`, which runs `deploy/run_eval.py`.
  4. The evaluation script:
     - Discovers `eval/*.test.json` test case files.
     - Substitutes placeholder project IDs with the actual project ID.
     - Runs `adk eval` with trajectory and rubric-based evaluations.
     - Optionally syncs results to Vertex AI GenAI Evaluation Service (when `--sync` is passed).
- **Secrets used**: `SRE_AGENT_ENCRYPTION_KEY`, `GOOGLE_CUSTOM_SEARCH_API_KEY`, `GITHUB_TOKEN`, `EVAL_PROJECT_ID`
- **Key env vars**: `RUNNING_IN_AGENT_ENGINE=true`, `STRICT_EUC_ENFORCEMENT=false`, `SRE_AGENT_ENFORCE_POLICY=false`

## Substitution Variables

These are configurable parameters passed to Cloud Build via `--substitutions` or trigger configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `_LOCATION` | GCP region for deployment | `us-central1` |
| `_BUCKET` | Cloud Storage staging bucket for Agent Engine artifacts | `your-staging-bucket-name` |
| `_GOOGLE_CUSTOM_SEARCH_ENGINE_ID` | Programmable Search Engine ID for research tools | `""` (empty) |
| `_GITHUB_REPO` | GitHub repository for issue/PR integration | `srtux/sre-agent` |
| `_SRE_AGENT_COUNCIL_ORCHESTRATOR` | Enable Council of Experts architecture | `""` (empty) |
| `_SRE_AGENT_SLIM_TOOLS` | Enable slim tool set (~20 tools on root agent) | `""` (empty) |

## Required Secrets (Google Cloud Secret Manager)

The pipeline reads secrets from Google Cloud Secret Manager (not GitHub Secrets). Configure the following secrets in your GCP project:

| Secret Name in Secret Manager | Cloud Build Env Var | Description |
|-------------------------------|---------------------|-------------|
| `sre-agent-encryption-key` | `SRE_AGENT_ENCRYPTION_KEY` | Encryption key for EUC token storage in session state. |
| `google-custom-search-api-key` | `GOOGLE_CUSTOM_SEARCH_API_KEY` | API key for Google Custom Search (research tools). |
| `github-token` | `GITHUB_TOKEN` | GitHub personal access token for repository integration. |
| `eval-project-id` | `EVAL_PROJECT_ID` | GCP project ID for running evaluations (optional; falls back to build project). |
| `gemini-api-key` | `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Gemini API key (mounted as Cloud Run secret). |
| `google-client-id` | `GOOGLE_CLIENT_ID` | OAuth client ID for frontend authentication (mounted as Cloud Run secret). |

> [!NOTE]
> The `eval-project-id` secret is optional. If not configured, evaluations will run against the same project used for the build. Set this secret to isolate evaluation workloads (e.g., to use a project with pre-populated telemetry data).

## Build Options

```yaml
options:
  logging: CLOUD_LOGGING_ONLY
```

Build logs are sent exclusively to Cloud Logging (not to Cloud Storage), keeping the build configuration lean.

## Manual Trigger

You can trigger the pipeline manually from the GCP Console under **Cloud Build > Triggers**, or via the `gcloud` CLI:

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_LOCATION=us-central1,_BUCKET=your-staging-bucket
```

For local deployment without Cloud Build, use the poe tasks:

```bash
uv run poe deploy        # Backend to Agent Engine
uv run poe deploy-web    # Frontend to Cloud Run
uv run poe deploy-all    # Full stack
uv run poe deploy-gke    # Full stack to GKE
```
