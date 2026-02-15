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

### Model Standardization on Gemini 2.5 GA

*   **Date**: January 27, 2026 (updated February 2026)
*   **Decision**: Standardize on Gemini 2.5 GA models for both Local Development and Agent Engine Deployment.
    *   **Local**: Use Gemini 2.5 GA models (`gemini-2.5-flash` / `gemini-2.5-pro`).
    *   **Agent Engine**: Use Gemini 2.5 GA models (`gemini-2.5-flash` / `gemini-2.5-pro`).
*   **Context**:
    Previously, local development used Gemini 3.0 Preview models while Agent Engine used Gemini 2.5. This was consolidated to use Gemini 2.5 everywhere to reduce behavioral discrepancies between environments and simplify testing.
*   **Rationale**:
    Using `sre_agent/model_config.py` centralizes model selection via the `get_model_name()` function. The function accepts `"fast"` or `"deep"` capability strings and returns `gemini-2.5-flash` or `gemini-2.5-pro` respectively. All agents and sub-agents should use this function rather than hardcoding model IDs.
*   **Implementation**:
    The `get_model_name()` function in `sre_agent/model_config.py` returns the appropriate model string. The `RUNNING_IN_AGENT_ENGINE` environment variable is still checked but both paths now return the same models. Includes OPT-10: Context caching configuration (`SRE_AGENT_CONTEXT_CACHING`).
*   **Action for Update**:
    When Gemini 3.0 reaches GA on Agent Engine, evaluate migration. The `get_model_name()` function is the single point of change.

### LLM Credential Injection Disabled

*   **Date**: February 2026
*   **Decision**: Do not inject End-User Credentials (EUC) into the Vertex AI Gemini client.
*   **Context**:
    Vertex AI's `GenerateContent` API rejects Google Sign-In (Web Client) access tokens with `401 ACCESS_TOKEN_TYPE_UNSUPPORTED`. Attempts to use the user's OAuth token for LLM calls consistently fail.
*   **Rationale**:
    Gemini must execute using the Service Account (ADC). Tools continue to use EUC by explicitly calling `get_credentials_from_tool_context()`. The credential injection code in `_inject_global_credentials()` in `agent.py` has been commented out with a detailed explanation.
*   **Implementation**:
    The `_inject_global_credentials()` function in `agent.py` instantiates the model object but no longer patches its credentials. The commented-out credential injection code is preserved for reference.

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

---

## Agent Architecture

### 3-Tier Request Router

*   **Date**: February 2026
*   **Decision**: Implement a 3-tier request router (`core/router.py`) as the first tool called on every user turn.
*   **Context**:
    Without routing, the root agent with ~90 tools would frequently misclassify queries, choosing overly complex investigation flows for simple data retrieval or using single tools when parallel analysis was needed.
*   **Rationale**:
    The rule-based router (`classify_routing()` in `council/intent_classifier.py`) classifies queries into DIRECT (simple retrieval), SUB_AGENT (specialist analysis), or COUNCIL (multi-signal investigation) tiers with zero LLM overhead. This reduces unnecessary sub-agent invocations and improves response latency for simple queries.
*   **Implementation**:
    The `route_request` tool in `core/router.py` returns a `BaseToolResponse` with routing guidance (tier, suggested tools/agent, investigation mode). The root agent's prompt instructs it to call this tool first.

### Council 2.0 Adaptive Panel Selection

*   **Date**: February 2026
*   **Decision**: Add an LLM-augmented adaptive classifier (`council/adaptive_classifier.py`) that considers session context for investigation mode selection.
*   **Context**:
    The rule-based intent classifier uses keyword matching which can be inaccurate for ambiguous queries or when session context (recent queries, alert severity, token budget) would change the optimal investigation mode.
*   **Rationale**:
    The adaptive classifier uses a lightweight LLM call to classify investigation mode, falling back to rule-based classification on any failure. It considers session history, alert severity, remaining token budget, and previous investigation modes.
*   **Implementation**:
    Enabled via `SRE_AGENT_ADAPTIVE_CLASSIFIER=true`. The `adaptive_classify()` function in `council/adaptive_classifier.py` formats a prompt with context and parses the LLM response. Falls back to `classify_intent_with_signal()` on any error.

### Tool Registry Centralization (OPT-4)

*   **Date**: February 2026
*   **Decision**: Create a single source of truth for all domain-specific tool sets in `council/tool_registry.py`.
*   **Context**:
    Sub-agents and council panels were independently defining their tool sets, leading to tool set drift where a panel might have a tool that its corresponding sub-agent lacked (or vice versa).
*   **Rationale**:
    A centralized registry ensures consistent tool availability across all agents. Shared tool sets (`SHARED_STATE_TOOLS`, `SHARED_REMEDIATION_TOOLS`, `SHARED_RESEARCH_TOOLS`, `SHARED_GITHUB_TOOLS`) are composed into domain-specific sets using Python list unpacking.
*   **Implementation**:
    Both `sub_agents/*.py` and `council/panels.py` import tool sets from `council/tool_registry.py`. Adding a new tool to a domain requires updating only the registry.

### Large Payload Handler

*   **Date**: February 2026
*   **Decision**: Implement automatic sandbox processing for oversized tool outputs (`core/large_payload_handler.py`).
*   **Context**:
    Tools like `list_log_entries` or `list_metric_descriptors` can return hundreds of thousands of items. Previously these were either sent raw to the LLM (exceeding context limits) or bluntly truncated at 200k chars (losing valuable data).
*   **Rationale**:
    The handler sits in the `after_tool_callback` chain before the truncation guard. When results exceed configurable thresholds, they are auto-summarized via the sandbox or returned with a compact sample plus a structured prompt for the LLM to generate analysis code.
*   **Implementation**:
    Integrated as the first stage of `composite_after_tool_callback` in `agent.py`. Uses `LocalCodeExecutor` or `SandboxExecutor` for processing. The tool-to-template mapping allows known data shapes to be processed automatically.
