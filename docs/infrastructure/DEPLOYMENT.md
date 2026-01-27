# Deployment Architecture

The SRE Agent uses a **parallel deployment strategy** to optimize build times by decoupling the backend (Agent Engine) deployment from the frontend (Cloud Run) build process.

## CI/CD Pipeline (`cloudbuild.yaml`)

The Cloud Build pipeline orchestrates the deployment in two parallel tracks:

### Pipeline Visualization

```mermaid
graph TD
    A[1. Install Dependencies] --> B[2. Fetch Resource ID]
    A --> C[3. Deploy Agent Backend]

    subgraph "Track A: Backend"
    C --> |Updates Agent Engine| C_End[Backend Live]
    end

    subgraph "Track B: Frontend"
    B --> |Provides ID| D[4. Build Docker Image]
    D --> E[5. Push Image]
    E --> F[6. Deploy Frontend]
    end

    style C fill:#d4f1f4,stroke:#333 -- Independent Track --
    style D fill:#d4f1f4,stroke:#333
    style E fill:#d4f1f4,stroke:#333
    style F fill:#d4f1f4,stroke:#333
```

### Steps Explained

1.  **Install Dependencies**: Sets up `uv` and Python environment.
2.  **Fetch Resource ID**: quickly looks up the *existing* Agent Engine resource ID (using `deploy/get_id.py`).
    *   *Purpose*: This ID is needed immediately by the frontend build (Track B).
    *   *Constraint*: This step fails if no agent exists (First Deployment must be manual).
3.  **Deploy Agent Backend (Track A)**:
    *   **Starts Immediately**: Does not wait for "Fetch Resource ID".
    *   **Logic**: Uses `deploy/deploy.py --create` to find the agent by name (`sre_agent`) and patch it.
    *   **Independence**: Since it finds the agent itself, it doesn't need the ID from step 2, allowing it to run in parallel.
4.  **Build Docker Image (Track B)**:
    *   **Waits For**: `fetch-resource-id` (Step 2).
    *   **Logic**: Builds the frontend container with `SRE_AGENT_ID` baked in as a build argument.
5.  **Push Image (Track B)**:
    *   **Waits For**: `build-image`.
    *   **Logic**: Pushes the container to GCR.
6.  **Deploy Frontend (Track B)**:
    *   **Waits For**: `push-image`.
    *   **Logic**: Deploys to Cloud Run with the `SRE_AGENT_ID` environment variable.

## First-Time Deployment

Because Step 2 (`fetch-resource-id`) expects an existing agent, the very first deployment **must be done manually** from a local machine or via a specific Cloud Build job that skips the fetch Step.

To deploy for the first time:

```bash
# 1. Create the Backend Agent
uv run python deploy/deploy.py --create --project_id YOUR_PROJECT_ID ...

# 2. Trigger the Cloud Build pipeline
gcloud builds submit ...
```

Once the agent exists, the CI/CD pipeline will work automatically.

## Environment Variables Strategy

*   **Agent Engine (Backend)**: Receives configuration via `deploy.py` (e.g., `STRICT_EUC_ENFORCEMENT`, encryption keys).
*   **Cloud Run (Frontend)**: Receives the **Agent Engine Resource ID** via two methods:
    1.  **Build Arg**: Baked into the image as a default.
    2.  **Env Var**: Injected at runtime by `cloudbuild.yaml` (overrides default).

## Failure Modes

*   **If Backend Fails, Frontend Succeeds**: The new Frontend will be calculating against the *old* Backend logic. This is generally safe for minor updates but requires care for breaking schema changes.
*   **If Frontend Fails**: The Backend might be updated but no UI changes are visible.
