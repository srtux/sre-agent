# Technical Decisions & Constraints

This document records significant architectural decisions, dependency constraints, and rationale for specific implementation patterns that might otherwise seem unconventional.

## Dependency Constraints

### Pydantic Runtime Monkeypatch (TypeAdapter Compatibility)

*   **Date**: January 25, 2026
*   **Decision**: Apply a runtime monkeypatch to `pydantic.TypeAdapter.__init__` in `sre_agent/api/app.py` instead of pinning `pydantic < 2.12.0`.
*   **Context**:
    Pydantic 2.12.0+ rigidly enforces a rule that `TypeAdapter` cannot be initialized with a `config` argument if the target type is a `BaseModel` (which has its own config). The `google-adk` library (v1.23.0) blindly passes a default config to `TypeAdapter` during tool schema generation, causing a fatal `PydanticUserError` on startup.
*   **Rationale**:
    Version pinning proved ineffective/fragile due to complex dependency trees and the fact that even some 2.11 versions (or environment mismatches) triggered the issue. A runtime patch that specifically intercepts this invalid call pattern is more robust. It allows the SRE Agent to use the latest Pydantic features (like the new JSON schema generator required by other components) while neutralizing the specific incompatibility in `google-adk`.
*   **Implementation**:
    The function `_patch_pydantic()` in `sre_agent/api/app.py` wraps `TypeAdapter.__init__`. It checks if `config` is present AND the type is a `BaseModel`. If so, it sets `config=None` before calling the original initializer.
*   **Action for Update**:
    Monitor `google-adk` releases. Once they remove the redundant `config` parameter from their internal `TypeAdapter` usage, the `_patch_pydantic()` call can be removed from `app.py`.

---

## Tool Architecture

### Direct API vs. MCP Fallback

*   **Decision**: Standardize on a "Direct API First, MCP Second" strategy for high-latency signals (Logs/Traces).
*   **Rationale**:
    MCP servers (Model Context Protocol) run as separate processes and can introduce overhead for high-volume data retrieval. By using Google Cloud's direct client libraries for primary fetching and reserving MCP for complex stateful operations, we achieve sub-second response times for data-heavy triage tasks.

---

## Model Support & Deployment Constraints

### Agent Engine GA Model Enforcement (Gemini 1.5)

*   **Date**: January 27, 2026
*   **Decision**: Standardize on Gemini 1.5 (Flash and Pro) for all environments (Local and Agent Engine) and prohibit the use of Gemini 3.0 or non-GA models.
*   **Context**:
    Agent Engine currently only supports GA (General Availability) models. Deploying an agent with Gemini 3 (e.g., `gemini-3-flash-preview`) results in a `404 NOT_FOUND` error in the cloud. Furthermore, because ADK agents are often instantiated at module import time, local settings (like `gemini-3`) can get "frozen" into the serialized agent state during deployment.
*   **Rationale**:
    Using Gemini 1.5 Flash/Pro ensures seamless deployment to Agent Engine. While newer preview models may offer advanced features, they break the core deployment pipeline. By enforcing Gemini 1.5 even in local development, we maintain parity and avoid "works locally, fails in cloud" scenarios.
*   **Implementation**:
    The `sre_agent/model_config.py` enforces `gemini-1.5-flash` for "fast" tasks and `gemini-1.5-pro` for "deep" tasks. All sub-agents and suggestions must use this configuration or hardcode 1.5 models.
*   **Action for Update**:
    Review Agent Engine support for future models (Gemini 2.0/3.0). Once they are GA on Agent Engine, `model_config.py` can be updated.
