# Auto SRE Documentation

Welcome to the Auto SRE documentation. This project uses a modular documentation structure to support both human developers and LLM agents.

## 📚 Documentation Structure

### [Project Plan](PROJECT_PLAN.md)
The living roadmap for Auto SRE development. **Check this first for current status.**

### [Architecture](architecture/)
Detailed design documents for the system's core components.
- [System Overview](architecture/system_overview.md): High-level architecture and component diagrams.
- [Project Structure](architecture/project_structure.md): Detailed directory tree and module descriptions.
- [Backend](architecture/backend.md): FastAPI application, middleware, and services.
- [Frontend](architecture/frontend.md): Flutter Web application and State Management.
- [Authentication](architecture/authentication.md): Security, OAuth, and Session Management.
- [Technical Decisions](architecture/decisions.md): Historic record of architectural choices.

### [Concepts](concepts/)
Core philosophies and abstract models driving the agent.
- [Autonomous Reliability](concepts/autonomous_reliability.md): The "Unrolled Codex" pattern and event loop.
- [Agent Orchestration](concepts/agent_orchestration.md): How the Core Squad (Trace Analyst, Log Analyst, etc.) works.
- [Observability](concepts/observability.md): Deep dive into traces, spans, and metrics analysis.
- [Memory & State](concepts/memory.md): How the agent remembers context across sessions.
- [Auth Learnings](concepts/auth_learnings.md): Evolution of the authentication system.
- [Roadmap](concepts/gcp_enhancements.md): Vision for the future of the SRE Agent.

### [Guides](guides/)
Practical instructions for using and developing the agent.
- [Getting Started](guides/getting_started.md): **Start Here**. Installation and configuration.
- [Development Guide](guides/development.md): The "Vibe Coding" handbook.
- [Testing Strategy](guides/testing.md): World-class testing standards.
- [Linting Rules](guides/linting.md): Zero-tolerance code quality policy.
- [Deployment](guides/deployment.md): How to deploy to Cloud Run and Agent Engine.
- [Evaluation](guides/evaluation.md): Benchmarking performance.
- [Debugging Connectivity](guides/debugging_connectivity.md): Troubleshooting network and API issues.
- [Debugging Telemetry](guides/debugging_telemetry_and_auth.md): Diagnosing missing traces or auth failures.
- [Debugging GenUI](guides/debugging_genui.md): Troubleshooting visual widget issues.

### [Reference](reference/)
API specifications and tool catalogs.
- [Configuration](reference/configuration.md): Environment variable reference.
- [API Reference](reference/api.md): Agent API and Protocol.
- [Tools Catalog](reference/tools.md): Complete list of available tools (BigQuery, Trace, etc.).
- [Security](reference/security.md): Encryption, key management, and data handling.

---

## 🤖 For AI Agents
If you are an LLM agent reading this, please start with [architecture/system_overview.md](architecture/system_overview.md) to understand the system topology, then check [guides/development.md](guides/development.md) for coding standards.
