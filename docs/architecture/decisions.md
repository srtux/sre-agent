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

### Agent Engine GA Model Enforcement (Gemini 2.5) vs Local Development (Gemini 3.0)

*   **Date**: January 27, 2026
*   **Decision**: Differentiate model usage between Local Development and Agent Engine Deployment.
    *   **Local**: Use Gemini 3.0 Preview models (`gemini-3-flash-preview` / `gemini-3-pro-preview`).
    *   **Agent Engine**: Use Gemini 2.5 GA models (`gemini-2.5-flash` / `gemini-2.5-pro`).
*   **Context**:
    Agent Engine currently only supports GA (General Availability) models, which includes Gemini 2.5 but NOT Gemini 3.0 Preview models yet. Deploying an agent hardcoded with Gemini 3 results in a `404 NOT_FOUND` error. However, for local development, we want the advanced reasoning capabilities of Gemini 3.
*   **Rationale**:
    Using `sre_agent/model_config.py` allows us to dynamically switch models based on the `RUNNING_IN_AGENT_ENGINE` environment variable. This ensures the agent is compatible with Cloud Run/Agent Engine while still allowing developers to benefit from the latest previews locally.
*   **Implementation**:
    The `get_model_name()` function in `sre_agent/model_config.py` detects the environment and returns the appropriate model string. All agents and sub-agents should use this function rather than hardcoding model IDs.
*   **Action for Update**:
    Monitor Agent Engine support for Gemini 3.0. Once it reaches GA on the platform, the transition can be made to use Gemini 3.0 everywhere.

---

## Frontend Architecture

### Flutter Service Injection via Provider vs. Singletons

*   **Date**: February 1, 2026
*   **Decision**: Migrate all Flutter services (Auth, Project, Session, etc.) from direct singleton access to **Provider-based Dependency Injection**.
*   **Context**:
    Initially, widgets like `ConversationPage` accessed services via `Service.instance` singletons. This made writing unit/widget tests extremely difficult, as these singletons often had transitive dependencies on SDKs (like `google_sign_in`) that crashed in headless test environments.
*   **Rationale**:
    Using the `Provider` pattern allows widgets to consume services from the `BuildContext`. This decoupling enables test suites to inject mock services at any level of the widget tree without modifying the underlying service implementation. It also aligns with Flutter's best practices for state management and reactive updates.
*   **Implementation**:
    1.  All services now support a static `mockInstance` for global override in non-widget code.
    2.  `SreNexusApp` (`lib/app.dart`) provides all services via `MultiProvider`.
    3.  `ConversationPage` and other widgets now use `context.read<T>()` or `context.watch<T>()` instead of `T.instance`.
    4.  A `test_helper.dart` utility provides `wrapWithProviders` for rapid setup of test environments with full mock coverage.
