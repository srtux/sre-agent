### Deployment and Infrastructure

AutoSRE supports multiple deployment modes, from local development to full cloud deployment on Google Cloud. The architecture separates the AI reasoning engine from the web frontend for flexibility and scalability.

### Deployment Options

| Mode | Command | Description |
|------|---------|-------------|
| **Local Development** | `uv run poe dev` | Full stack locally -- FastAPI backend (port 8001) + Flutter web frontend |
| **Backend Only** | `uv run poe web` | FastAPI server only (useful for API development) |
| **Terminal Agent** | `uv run poe run` | CLI agent via `adk run` (no web UI) |
| **Cloud Run** | `uv run poe deploy-web` | Frontend to Cloud Run |
| **Agent Engine** | `uv run poe deploy` | Backend to Vertex AI Agent Engine |
| **Full Cloud** | `uv run poe deploy-all` | Both frontend (Cloud Run) and backend (Agent Engine) |
| **GKE** | `uv run poe deploy-gke` | Full stack to Google Kubernetes Engine |

### Dual-Mode Execution

AutoSRE supports two execution modes, controlled by the `SRE_AGENT_ID` environment variable:

**Local Mode** (`SRE_AGENT_ID` not set):
- The agent runs in-process within the FastAPI server.
- No external Agent Engine dependency.
- Best for development, testing, and small-scale use.
- All LLM calls go directly to the Gemini API.

**Remote Mode** (`SRE_AGENT_ID` set):
- The FastAPI server acts as a proxy, forwarding requests to Vertex AI Agent Engine.
- The Agent Engine hosts the reasoning logic, tools, and sub-agents.
- Provides managed scaling, monitoring, and enterprise features.
- Your identity is propagated via EUC (End-User Credentials) to the agent.

### Cloud Run Frontend

When deployed via Cloud Run:
- **Port**: 8080 (Cloud Run standard)
- **IAM**: Requires `roles/run.invoker` for access and `roles/secretmanager.secretAccessor` for secrets
- **Secrets**: Uses Secret Manager for `gemini-api-key` and `google-client-id`
- **Auth**: OAuth 2.0 with redirect URI matching the Cloud Run service URL

### Vertex AI Agent Engine

The core reasoning engine as a managed Vertex AI resource:
- **Streaming**: Direct streaming from Agent Engine to the frontend ensures responsive chat
- **EUC**: Your identity (OAuth token) is propagated to the agent, ensuring it only accesses data you are authorized to see
- **Monitoring**: Agent Engine provides built-in traces for debugging agent behavior
- **Scaling**: Managed auto-scaling based on concurrent investigation load

### GKE Deployment

For full control over the infrastructure:
- Kubernetes manifests in `deploy/k8s/`
- Both frontend and backend run as Kubernetes deployments
- Supports custom networking, security policies, and resource limits
- Horizontal pod autoscaling for the backend

### Troubleshooting Deployments

**Dashboard fails to load:**
1. Check the Logs Explorer in the GCP Console for the `autosre` service.
2. Verify `SRE_AGENT_ID` is set correctly in the environment variables (for remote mode).
3. Ensure your OAuth redirect URI includes the Cloud Run URL.
4. Check that Secret Manager secrets are accessible to the Cloud Run service account.

**Agent Engine connection issues:**
1. Verify the Agent Engine resource is deployed: `uv run poe list`
2. Check that the service account has `roles/aiplatform.user` permissions.
3. Ensure the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` variables match the Agent Engine deployment.

**Local development issues:**
1. Run `uv run poe sync` to ensure all dependencies are installed.
2. Check that `GOOGLE_CLOUD_PROJECT` is set to a valid project ID.
3. For the Flutter frontend, ensure Flutter SDK is installed and `flutter pub get` has been run.
