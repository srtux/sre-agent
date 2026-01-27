---
artifact: design
change: setup-cicd-pipeline
status: draft
---

# Design: GCP Native CI/CD with Cloud Build

## Context
The current deployment process is manual. The user wants to automate this but prefers using GCP's native CI/CD (Cloud Build) to handle the deployment, likely for better integration with IAM and to avoid handling complex GCP credentials in GitHub Actions.

## Goals / Non-Goals

**Goals:**
- Automate deployment of both Agent Engine (backend) and Cloud Run (frontend).
- Use Cloud Build Triggers for deployment.
- Keep GitHub Actions for fast CI (lint/test).
- Ensure the Cloud Build service account has appropriate IAM permissions.

**Non-Goals:**
- Setting up a multi-region deployment.
- Implementing a full blue/green deployment strategy (Cloud Run handles revisions automatically).

## Decisions

### 1. Cloud Build for Deployment
Cloud Build will be the primary deployment engine. It will be triggered by GitHub via a Cloud Build Trigger. This keeps the "deployment authority" within GCP.

#### Why?
- **IAM Integration**: Cloud Build uses a service account that can be easily granted permissions within the same GCP project (e.g., Vertex AI User, Cloud Run Developer).
- **Security**: No need to export Service Account keys to GitHub.

### 2. Hybrid CI/CD
We will use GitHub Actions for the "Inner Loop" (linting, testing) and Cloud Build for the "Outer Loop" (building, deploying).

- **GitHub Action**: Runs on every PR.
- **Cloud Build Trigger**: Runs on merge to `main`.

### 3. Build & Deploy Orchestration (`cloudbuild.yaml`)
The `cloudbuild.yaml` will perform the following steps:
1.  **Environment Setup**: Install `uv` and dependencies.
2.  **Deploy Backend**: Run `uv run poe deploy`. We will need to capture the generated `resource_name`.
3.  **Build Frontend**: Build the unified Docker image using the existing `Dockerfile`.
4.  **Deploy Frontend**: Deploy to Cloud Run using `gcloud run deploy`, injecting the captured Agent Engine URL.

## Risks / Trade-offs

- **Risk**: Capturing the resource ID from `deploy.py` in a shell script/Cloud Build step can be brittle if the output format changes.
- **Trade-off**: Running the build in Cloud Build takes longer than local builds, but ensures a clean environment.
- **Risk**: GitHub and GCP need a "Link" established (Cloud Build GitHub App). This requires a one-time setup by the project owner.
