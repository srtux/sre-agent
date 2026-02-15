# Deployment Scripts

This directory contains all deployment orchestration scripts, Kubernetes manifests, and IAM setup tools for AutoSRE.

For the full deployment guide, see [docs/guides/deployment.md](../docs/guides/deployment.md).
For CI/CD pipeline architecture, see [docs/infrastructure/DEPLOYMENT.md](../docs/infrastructure/DEPLOYMENT.md).

## Quick Start

```bash
# Deploy full stack (backend + frontend)
uv run poe deploy-all

# Deploy backend only (Agent Engine)
uv run poe deploy

# Deploy frontend only (Cloud Run)
uv run poe deploy-web

# Deploy to GKE
uv run poe deploy-gke --cluster <CLUSTER_NAME> --region <REGION>

# List deployed agents
uv run poe list
```

## Scripts

| Script | Purpose | Target |
|--------|---------|--------|
| `deploy.py` | Deploy/update the ADK agent | Vertex AI Agent Engine |
| `deploy_web.py` | Deploy the Flutter + FastAPI frontend | Cloud Run |
| `deploy_gke.py` | Deploy the unified container to GKE | Google Kubernetes Engine |
| `deploy_all.py` | Orchestrate full-stack deployment (parallel when possible) | Agent Engine + Cloud Run |
| `grant_permissions.py` | Grant IAM roles to the service account | IAM |
| `get_id.py` | Look up existing Agent Engine resource ID by name | Vertex AI |
| `setup_agent_identity_iam.sh` | Grant IAM roles to Agent Identity principal | IAM |
| `verify_agent_identity.py` | Verify Agent Identity is active and has correct bindings | Vertex AI |

## Subdirectories

| Directory | Contents |
|-----------|----------|
| `k8s/` | Kubernetes manifests (`deployment.yaml`, `service.yaml`) for GKE deployment |

## Resource Requirements

| Deployment Target | Memory | CPU | Notes |
|-------------------|--------|-----|-------|
| Cloud Run | 16 GiB | 4 vCPUs | Timeout: 300s, `WEB_CONCURRENCY=2` |
| GKE | Configurable | Configurable | Set via `deployment.yaml` resource limits |
| Agent Engine | Managed | Managed | `min_instances=1` by default |

## Secret Manager Secrets

The following secrets must exist in Google Cloud Secret Manager:

| Secret Name | Required By | Purpose |
|-------------|-------------|---------|
| `gemini-api-key` | Cloud Run, Cloud Build | Gemini API key for LLM calls |
| `google-client-id` | Cloud Run | OAuth Client ID for frontend |
| `sre-agent-encryption-key` | Cloud Run, Agent Engine, Cloud Build | Fernet key for session token encryption |
| `google-custom-search-api-key` | Cloud Build | Google Custom Search API key (research tools) |
| `github-token` | Cloud Build | GitHub personal access token |
| `eval-project-id` | Cloud Build (optional) | Separate project for running evals |

## Environment Variable Propagation

Variables flow from local environment or Secret Manager to deployment targets:

```
Local .env / Secret Manager
    |
    ├──► deploy.py ──► Agent Engine (baked at deploy time)
    |    - SRE_AGENT_ENCRYPTION_KEY
    |    - GOOGLE_CUSTOM_SEARCH_API_KEY (if set)
    |    - GOOGLE_CUSTOM_SEARCH_ENGINE_ID (if set)
    |    - GITHUB_TOKEN (if set)
    |    - GITHUB_REPO (if set)
    |    - Telemetry/logging config
    |
    └──► deploy_web.py ──► Cloud Run (runtime)
         - Secrets via --set-secrets (from Secret Manager)
         - Env vars via --set-env-vars
```
