# Project Overview: Auto SRE Agent

The **Auto SRE Agent** is an AI-assisted system designed to automate Site Reliability Engineering (SRE) tasks, primarily targeting Google Cloud Platform (GCP). It follows the "Council of Experts" pattern, where a main orchestrator delegates tasks to specialized sub-agents (e.g., for traces, logs, metrics).

## Core Capabilities
- Automated incident investigation and diagnostics.
- Multimodal data analysis (Logs, Metrics, Traces).
- Proactive signal monitoring and alerting.
- Generative UI (GenUI) for interactive tool outputs.
- Integration with GCP via both Direct APIs and Model Context Protocol (MCP).

## Directory Structure
- `sre_agent/`: Main Python backend codebase.
    - `agent.py`: Root orchestrator agent.
    - `api/`: FastAPI routers and middleware.
    - `tools/`: Tool implementations (GCP clients, BigQuery/MCP, analysis).
    - `sub_agents/`: Specialized agent definitions.
    - `services/`: Core infrastructure (sessions, storage, auth).
- `autosre/`: Flutter Web frontend.
- `tests/`: Comprehensive test suite for backend.
- `docs/`: Architecture diagrams, design docs, and guides.
