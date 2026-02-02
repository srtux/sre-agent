### Deployment & Infrastructure

AutoSRE is built for the cloud but optimized for local speed.

#### Cloud Run (Frontend & Proxy)
When deployed via `uv run poe deploy-all`, the Flutter UI and FastAPI backend are packaged into a single container:
- **Port**: 8080 (standard for Cloud Run)
- **IAM**: Requires `roles/run.invoker` and `roles/secretmanager.secretAccessor`.
- **Secrets**: Relies on `gemini-api-key` and `google-client-id` from Secret Manager.

#### Vertex AI Agent Engine (The Brain)
The core reasoning engine lives in a Vertex AI Reasoning Engine resource.
- **Latency**: Direct streaming from Agent Engine to Cloud Run ensures a responsive chat experience.
- **EUC**: Your identity is propagated to the agent, ensuring it only sees what you see.

#### Troubleshooting Deployments
If the dashboard fails to load:
1.  Check the "Logs Explorer" in the GCP Console for the `autosre` service.
2.  Verify `SRE_AGENT_ID` is set in the environment variables.
3.  Ensure your OAuth redirect URI includes the Cloud Run URL.
