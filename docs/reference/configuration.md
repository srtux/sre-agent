# Configuration Reference

This document details all environment variables used to configure the Auto SRE Agent.

## Core Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | The GCP Project ID where the agent is running. | Yes | - |
| `GOOGLE_CLOUD_LOCATION` | The GCP Region (e.g., `us-central1`). | Yes | - |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID for the Flutter Frontend. | Yes | - |
| `SRE_AGENT_ENCRYPTION_KEY` | AES-256 key for encrypting session tokens. | Yes | - |

## Execution Modes

| `SRE_AGENT_ID` | If set, the backend forwards requests to this Vertex AI Agent Engine resource. If unset, runs locally. | - |
| `STRICT_EUC_ENFORCEMENT` | If `true`, fails requests if user credentials are missing. If `false`, falls back to service account (NOT RECOMMENDED for production). | `false` |
| `CORS_ALLOW_ALL` | If `true`, allows all origins in FastAPI middleware. Useful for development. | `false` |
| `SECURE_COOKIES` | If `true`, session cookies are marked as `Secure`. Set to `false` for local `http` dev. | `true` |

## Telemetry & Debugging

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG_TELEMETRY` | Enable verbose OpenTelemetry logs. | `false` |
| `DEBUG_AUTH` | Enable verbose authentication logs. | `false` |
| `LOG_LEVEL` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` |
| `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY` | Enable telemetry within the Agent Engine runtime. | `false` |

## External Integrations

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_ARIZE` | Enable Arize AX observability. | `false` |
| `ARIZE_SPACE_ID` | Arize Space ID. | - |
| `ARIZE_API_KEY` | Arize API Key. | - |
| `TRACE_PROJECT_ID` | Override project for Cloud Trace queries (if different from host). | `GOOGLE_CLOUD_PROJECT` |
| `GEMINI_API_KEY` | Your Google API Key (if not using ADC/Service Account). | - |
| `GOOGLE_API_KEY` | Alias for `GEMINI_API_KEY`. | - |

## Storage & Sessions

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_DATABASE_SESSIONS` | Force using SQLite sessions. | `true` |
| `SESSION_DB_PATH` | Path to the SQLite session database. | `.sre_agent_sessions.db` |
| `USE_FIRESTORE` | Backend for session storage in production. | `false` (Auto-detected in Cloud Run) |

## Server Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Listening port for the FastAPI server. | `8001` |
| `HOST` | Listening host for the FastAPI server. | `0.0.0.0` |

## Deployment Variables

Used by `deploy/` scripts.

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_STORAGE_BUCKET` | Staging bucket for Agent Engine artifacts. |
