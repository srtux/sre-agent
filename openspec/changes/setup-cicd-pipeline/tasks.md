---
artifact: tasks
change: setup-cicd-pipeline
status: draft
---

# Tasks: GCP Native CI/CD

## 1. Cloud Build Configuration

- [ ] 1.1 Create `cloudbuild.yaml` to orchestrate deployment.
    - [ ] 1.1.1 Step: Initialize environment and install dependencies.
    - [ ] 1.1.2 Step: Deploy Agent Engine backend and capture resource ID.
    - [ ] 1.1.3 Step: Build unified Docker image.
    - [ ] 1.1.4 Step: Deploy Frontend to Cloud Run.
- [ ] 1.2 Update `.gcloudignore` to ensure all necessary files (like `pyproject.toml`, `sre_agent/`, etc.) are included in the build context.

## 2. Infrastructure & Permissions (Documentation)

- [ ] 2.1 Document how to create the Cloud Build trigger in GCP.
- [ ] 2.2 Document required IAM roles for the Cloud Build service account.
    - `roles/aiplatform.user`
    - `roles/run.developer`
    - `roles/iam.serviceAccountUser`
    - `roles/storage.admin`
    - `roles/secretmanager.secretAccessor`

## 3. GitHub Action Refinement

- [ ] 3.1 Update `.github/workflows/python-app.yml` to ensure it only runs CI (lint/test) and does not attempt any deployment, providing a clean separation of concerns.

## 4. Verification

- [ ] 4.1 Perform a dummy manual run of Cloud Build via CLI to verify the `cloudbuild.yaml` logic.
- [ ] 4.2 Validate that the unified Docker image builds correctly under the Cloud Build environment.
