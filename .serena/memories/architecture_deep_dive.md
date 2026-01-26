# Architecture Deep Dive

The SRE Agent is a modular system that acts as an AI diagnostic tool for GCP observability data.

## Component Topology
The system is divided into four main layers:
1. **Frontend**: Flutter Web UI with GenUI protocol for interactive widgets.
2. **FastAPI Backend (Proxy)**: Acts as an orchestrator and stateful proxy. It handles Auth, MiddleWare, and Session storage.
3. **Vertex AI (Reasoning Engine)**: Powered by Google ADK. Contains the Root Agent, specialized Sub-Agents, and long-term Memory Bank.
4. **Google Cloud (Observability)**: Integration points for Cloud Trace, Logging, Monitoring, and BigQuery (OTel data).

## Execution Modes
- **Local Development Mode**: Runs Agent logic directly in the FastAPI process for fast iteration. Uses local SQLite/JSON storage.
- **Managed Production Mode**: Backend acts as a Proxy for the managed Vertex AI Agent Engine. Propagates credentials via Session State to the reasoning engine.

## Core Interaction Patterns
- **Hybrid Auth**: Combines Google SSO with secure backend session cookies (`sre_session_id`).
- **ReAct Loop**: Reasoning + Acting pattern for step-by-step diagnostic investigations.
- **GenUI**: Rich UI events emitted by the backend to render Flutter widgets (waterfalls, charts, etc.) directly in the chat.
