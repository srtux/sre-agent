---
artifact: specs
change: setup-cicd-pipeline
status: draft
---

# Specs: Continuous Deployment

## ADDED Requirements

### Requirement: Automated Stack Deployment
The system SHALL automatically deploy the full stack (Agent Engine backend and Cloud Run frontend) upon a merge to the `main` branch.

#### Scenario: Successful full-stack deployment
- **WHEN** a commit is merged into `main`
- **THEN** a Cloud Build job starts
- **AND** it successfully updates the Vertex AI Agent Engine
- **AND** it builds a new Docker image for the frontend
- **AND** it deploys the new image to Cloud Run with the updated backend URL

### Requirement: Service Account Permission Isolation
Deployment SHALL be performed using a dedicated Cloud Build service account with the minimum necessary IAM permissions.

#### Scenario: Verification of permissions
- **WHEN** Cloud Build starts
- **THEN** it uses its project-internal identity to authenticate with Vertex AI and Cloud Run
- **AND** no external service account keys are stored in GitHub Actions

### Requirement: Unified Build Context
The build process SHALL use a unified `Dockerfile` that packages both the Flutter web frontend and the Python backend into a single container.

#### Scenario: Building the unified image
- **WHEN** `docker build` is called in Cloud Build
- **THEN** it correctly copies the built Flutter artifacts and installs Python dependencies
- **AND** produce a runnable image for Cloud Run
