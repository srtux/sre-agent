### Troubleshooting the Agent

Sometimes the agent might get stuck or provide an unexpected answer. Here is how to fix it.

#### 1. "I don't have permission"
- **Cause**: The session token may have expired or you don't have the necessary IAM roles.
- **Fix**: Refresh the page to re-authenticate or check your roles in the GCP console (requires `roles/viewer` at minimum).

#### 2. Hallucinations or Loop
- **Cause**: The context window may be cluttered or the agent is in a reasoning loop.
- **Fix**: Use the "New Investigation" button to start a fresh thread.

#### 3. Missing Tools
- **Cause**: The agent failed to register MCP tools during startup.
- **Fix**: Check the backend logs for "MCP Connection Failed". Ensure your tool config is correct.

#### 4. UI Rendering Issues
- **Cause**: Generative UI (GenUI) failure.
- **Fix**: Click the "Raw Response" toggle (if available) to see the text-only output.
