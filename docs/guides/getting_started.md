# Getting Started with Auto SRE

This guide covers the prerequisites, installation, and configuration required to run the Auto SRE Agent.

## Prerequisites

*   **Python**: 3.10 or higher
*   **Google Cloud SDK**: Installed and configured (`gcloud auth login`)
*   **GCP Project**: Access to a project with Cloud Trace enabled

## Installation

We use `uv` for dependency management.

```bash
# 1. Install dependencies (Python + Flutter)
uv run poe sync

# 2. Configure environment
cp .env.example .env
```

## Configuration

Edit your `.env` file with the following required variables.

### Required Settings

```bash
# Your Google Cloud Project ID
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1

# Google OAuth Client ID (for Frontend)
# Create this in GCP Console > APIs & Services > Credentials
GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com

# Encryption Key for Session Data
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SRE_AGENT_ENCRYPTION_KEY=your-secure-encryption-key
```

### Optional Settings

```bash
# Enable Remote Agent Engine (Production Mode)
# SRE_AGENT_ID=projects/xxx/locations/xxx/reasoningEngines/xxx

# Strict End-User Credential Enforcement
STRICT_EUC_ENFORCEMENT=false

# Arize Observability
USE_ARIZE=false
```

## Running the Application

### Development Mode (Local)
Run the entire stack (FastAPI Backend + Flutter Frontend) locally.

```bash
uv run poe dev
```
*   **Backend**: http://localhost:8001
*   **Frontend**: http://localhost:3000

Alternatively, run them separately:
```bash
# Backend only
uv run poe web

# Frontend only (in separate terminal)
cd autosre && flutter run -d chrome
```

### Production Mode (Remote)
Deploy to Vertex AI Agent Engine and Cloud Run.

```bash
# Deploy full stack
uv run poe deploy-all
```

See [Deployment Guide](deployment.md) for detailed production instructions.

## Verification
1. Open the frontend URL.
2. Sign in with Google.
3. Type "Hello" to verify the agent responds.
4. Try "Analyze traces for service X" to verify GCP connectivity.
