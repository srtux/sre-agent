---
artifact: proposal
change: setup-cicd-pipeline
status: draft
---

# Proposal: CI/CD Pipeline for GCP Deployment

## Context
The user wants to automate the deployment process for the SRE Agent. Currently, deployments are triggered manually using `uv run poe deploy-all`. The goal is to set up a CI/CD pipeline that automatically deploys the frontend and backend whenever code is merged into the `main` branch.

## Benefits
- **Automation**: Reduces manual effort and potential for human error.
- **Consistency**: Ensures every merge to `main` is tested and deployed in a reproducible environment.
- **Speed**: Speeds up the delivery cycle.

- Use **Cloud Build Triggers** in GCP to handle the deployment.
- Configure a Cloud Build trigger that listens to the GitHub repository for merges to the `main` branch.
- The workflow will:
    1. GitHub Action: Runs tests and linting on every PR/push.
    2. Cloud Build Trigger: Automatically starts upon merge to `main`.
    3. Cloud Build: Executes the build and deployment logic defined in `cloudbuild.yaml`.
    4. Cloud Build: Deploys the backend to Vertex AI Agent Engine.
    5. Cloud Build: Builds the unified Docker image and deploys it to Cloud Run.

## Capabilities

### New Capabilities
- `continuous-deployment`: Automated pipeline for deploying the SRE Agent stack to GCP.

### Modified Capabilities
- (None)

## Impact
- **GitHub Repository**: New workflow file and required secrets/variables.
- **GCP Project**: Requires appropriate permissions for the service account/identity used by GitHub Actions.
- **Deployment Scripts**: No changes expected to existing scripts, but they will be orchestrated by the CI/CD pipeline.
