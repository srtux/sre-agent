# Autonomous Reliability Architecture

**Status**: Implemented (Phases 1-4 Complete)
**Last Updated**: 2026-02-15
**Author**: Architecture Team

---

## Overview

This document describes the architectural foundation of the SRE Agent as a **Stateful, Event-Driven Harness** based on the "Unrolled Codex" pattern and Google's Agent Development Kit (ADK). The core components -- Runner, PromptComposer, ContextCompactor, PolicyEngine, and GraphService -- are fully implemented and integrated.

---

## Core Philosophy

1. **The Harness is the Product**: The model is just a component. The logic lives in the Event Loop, not the prompt.
2. **Stateless Execution, Stateful Session**: The agent supports Zero-Downtime Restart (ZDR). Context is reconstructed from a persistent event log every turn.
3. **Epistemic Opacity**: SRE is a search problem. We do not guess; we traverse a Knowledge Graph and test hypotheses using Causal Inference.
4. **Safety as a Gate**: The model never executes code directly. It emits intents; the Harness intercepts, validates, and executes.

---

## Architecture Components

### 1. The Unrolled Loop (Codex Pattern)

```
+-----------------------------------------------------------------------------+
|                           THE UNROLLED EXECUTION MODEL                       |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +------------------+     +------------------+     +--------------------+    |
|  |   User Request   | --> |     Runner       | --> |   LLM Response     |    |
|  |   (External)     |     |   (Harness)      |     |   (Intent Only)    |    |
|  +------------------+     +------------------+     +--------------------+    |
|                                   |                          |               |
|                                   v                          v               |
|                          +----------------+         +----------------+       |
|                          | Session Store  | <-------|  Policy Engine |       |
|                          | (Event Log)    |         | (Intercept)    |       |
|                          +----------------+         +----------------+       |
|                                                              |               |
|                                                              v               |
|                                                     +----------------+       |
|                                                     | Tool Executor  |       |
|                                                     | (Safe Execute) |       |
|                                                     +----------------+       |
|                                                                              |
+-----------------------------------------------------------------------------+
```

**Key Principles:**
- **No Internal Memory Loops**: Remove any `while True:` inside LLM logic
- **Stateless Execution**: Each turn reconstructs context from event log
- **External Loop Control**: The Runner manages the execution cycle

The Runner (`sre_agent/core/runner.py`) implements the `RunnerConfig` dataclass with configurable policy enforcement (`SRE_AGENT_ENFORCE_POLICY`), context compaction, and three-tier prompt composition.

### 2. Three-Tier Prompt Composition

```python
class PromptComposer:
    """Builds prompts dynamically each turn from three components."""

    def compose(self, session: Session, user_message: str) -> list[Content]:
        return [
            self.system_role(),      # Immutable personality + physics
            self.developer_role(),   # Hard constraints + domain context
            self.user_role(session, user_message)  # Session history
        ]
```

#### Tier 1: System Role (Immutable)
```
You are an SRE Agent specialized in Google Cloud Observability.
Your purpose is to analyze telemetry data and identify root causes.
You operate in a SANDBOXED environment with READ-ONLY access.
```

#### Tier 2: Developer Role (Domain Context)
```
## Hard Constraints
- You may NOT execute any write operations without explicit approval
- All tool calls are intercepted and validated before execution
- Follow the OODA loop: Observe -> Orient -> Decide -> Act

## Domain Context
[INJECTED RUNBOOK.md CONTENT]
[CURRENT PROJECT: project-id]
[ACTIVE ALERTS: ...]
```

#### Tier 3: User Role (Session History)
```
## Working Context
[Summary of past tool outputs - compacted]
[Recent 5 raw events]

## Current Request
[User's message]
```

The `PromptComposer` is implemented in `sre_agent/core/prompt_composer.py` and provides `DomainContext` and `SessionSummary` dataclasses. The `get_prompt_composer()` factory returns a singleton instance.

### 3. Context Engineering (Sliding Window)

```
+-----------------------------------------------------------------------------+
|                        CONTEXT COMPACTION STRATEGY                           |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Full Event Log (Persisted)                                                  |
|  +- Event 1: UserMessage("Investigate latency spike")                       |
|  +- Event 2: ModelThought("Starting aggregate analysis")                    |
|  +- Event 3: ToolOutput(analyze_aggregate_metrics -> 50KB JSON)             |
|  +- Event 4: ToolOutput(fetch_trace -> 20KB trace data)                     |
|  +- Event 5: ModelThought("Found bottleneck in db-service")                 |
|  +- ...                                                                      |
|  +- Event N: UserMessage("What about the logs?")                            |
|                                                                              |
|  +-----------------------------------------------------------------+        |
|  |                     CONTEXT COMPACTION                           |        |
|  +-----------------------------------------------------------------+        |
|  |                                                                   |       |
|  |  Working Context (Sent to LLM):                                   |       |
|  |  +--------------------------------------------------------------+ |       |
|  |  | SUMMARY (Compacted from Events 1-N-5):                        | |       |
|  |  | - User asked about latency spike in checkout-service          | |       |
|  |  | - Aggregate analysis found db-service as bottleneck           | |       |
|  |  | - Trace abc123 shows 1.2s delay in database-proxy span        | |       |
|  |  | - 4 log patterns identified: 2 errors, 2 warnings            | |       |
|  |  +--------------------------------------------------------------+ |       |
|  |  +--------------------------------------------------------------+ |       |
|  |  | RECENT RAW EVENTS (Events N-4 to N):                          | |       |
|  |  | [Full content of last 5 events]                               | |       |
|  |  +--------------------------------------------------------------+ |       |
|  |                                                                   |       |
|  +-----------------------------------------------------------------+        |
|                                                                              |
+-----------------------------------------------------------------------------+
```

**Compaction Rules** (from `CompactionConfig` in `sre_agent/core/context_compactor.py`):
1. **Token Budget**: Keep working context under 32K tokens (configurable `token_budget`)
2. **Summarizer Trigger**: When raw events exceed 24K tokens (configurable `compaction_trigger_tokens`)
3. **Summary Retention**: Summaries are stored as `CompactionEvent` in the log
4. **Recency Bias**: Last 5 events always sent in full (configurable `recent_events_count`)
5. **Minimum Threshold**: At least 10 events before considering compaction (`min_events_for_compaction`)

The `ContextCompactor` class produces a `WorkingContext` dataclass containing the summary, recent events, token estimate, and compaction metadata. The `Summarizer` service (`sre_agent/core/summarizer.py`) handles LLM-based event summarization.

### 4. The Reasoning Engine (OODA Loop)

```
+-----------------------------------------------------------------------------+
|                           OODA REASONING LOOP                                |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +------------+     +------------+     +------------+     +------------+     |
|  |  OBSERVE   | --> |   ORIENT   | --> |   DECIDE   | --> |    ACT     |     |
|  |            |     |            |     |            |     |            |     |
|  | Gather     |     | Map to     |     | Form       |     | Execute    |     |
|  | Telemetry  |     | Knowledge  |     | Hypothesis |     | Synthetic  |     |
|  | Signals    |     | Graph      |     |            |     | Test       |     |
|  +------------+     +------------+     +------------+     +------------+     |
|        |                  |                  |                  |             |
|        v                  v                  v                  v             |
|  +--------------------------------------------------------------------+     |
|  |                         EVALUATE                                    |     |
|  |                                                                      |    |
|  |  - Did the test confirm or refute the hypothesis?                   |     |
|  |  - Update confidence scores in the Knowledge Graph                  |     |
|  |  - If refuted, return to OBSERVE with new constraints               |     |
|  +--------------------------------------------------------------------+     |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### 5. GraphService (Dependency Mapping)

The `GraphService` (`sre_agent/core/graph_service.py`) manages the service dependency knowledge graph, enabling blast radius analysis and causal inference.

```python
class ServiceType(str, Enum):
    COMPUTE = "compute"      # App servers, functions
    DATABASE = "database"    # SQL, NoSQL databases
    CACHE = "cache"          # Redis, Memcache
    QUEUE = "queue"          # Pub/Sub, Kafka
    EXTERNAL = "external"    # Third-party APIs
    GATEWAY = "gateway"      # API gateways, load balancers
    STORAGE = "storage"      # GCS, S3
    UNKNOWN = "unknown"

class EdgeType(str, Enum):
    CALLS = "calls"              # Synchronous call
    READS_FROM = "reads_from"    # Data read
    WRITES_TO = "writes_to"      # Data write
    SUBSCRIBES = "subscribes"    # Async subscription
    PUBLISHES = "publishes"      # Async publish
    DEPENDS_ON = "depends_on"    # Generic dependency

@dataclass
class DependencyNode:
    """A node in the service dependency graph."""
    service_name: str
    service_type: ServiceType = ServiceType.UNKNOWN
    namespace: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    avg_latency_ms: float | None = None
    error_rate: float | None = None
    request_count: int = 0

@dataclass
class DependencyEdge:
    """An edge representing a dependency between services."""
    source: str
    target: str
    edge_type: EdgeType
    latency_p50: float | None = None
    error_rate: float | None = None

class GraphService:
    """Manages the service dependency knowledge graph."""

    async def build_from_traces(self, traces: list[Trace]) -> DependencyGraph:
        """Build dependency graph from trace data."""

    async def get_upstream(self, service: str) -> list[DependencyNode]:
        """Get all services that call this service."""

    async def get_downstream(self, service: str) -> list[DependencyNode]:
        """Get all services this service depends on."""

    async def get_blast_radius(self, service: str) -> BlastRadiusReport:
        """Calculate the impact if this service fails."""
```

### 6. Policy Engine (Safety Layer)

The Policy Engine (`sre_agent/core/policy_engine.py`) intercepts and validates tool calls before execution. It classifies tools into access levels and enforces approval workflows.

```
+-----------------------------------------------------------------------------+
|                           POLICY ENGINE                                      |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Tool Call Intent                                                            |
|       |                                                                      |
|       v                                                                      |
|  +----------------+                                                          |
|  | Classification |-------------------------------------------+             |
|  | RO / RW / ADMIN|                                           |             |
|  +----------------+                                           |             |
|       |                                                        |             |
|       +--- READ_ONLY ---> Execute Immediately                 |             |
|       |                                                        |             |
|       +--- WRITE ---------> +----------------------------+    |             |
|       |                     | Human Approval Required     |    |             |
|       |                     |                             |    |             |
|       |                     | Emit: HumanApprovalEvent   |    |             |
|       |                     | Pause: Execution Loop      |    |             |
|       |                     | Wait:  HumanApproval       |    |             |
|       |                     +----------------------------+    |             |
|       |                              |                         |             |
|       |                              v                         |             |
|       |                     +----------------------------+    |             |
|       |                     | Approval Received?         |    |             |
|       |                     | YES: Execute with audit    |    |             |
|       |                     | NO:  Return rejection      |    |             |
|       |                     +----------------------------+    |             |
|       |                                                        |             |
|       +--- ADMIN ----------> Requires Approval (Experimental) |             |
|                                                                |             |
+-----------------------------------------------------------------------------+
```

#### Tool Access Levels

| Category | Access | Examples | Approval | Status |
|----------|--------|----------|----------|--------|
| READ_ONLY | RO | `fetch_trace`, `list_logs`, `query_promql` | Auto | Full |
| WRITE | RW | `restart_pod`, `scale_deployment` | Human Required | Full |
| ADMIN | RESTRICTED | `delete_resource`, `modify_iam` | Approval Required | EXPERIMENTAL |

#### Tool Categories

The policy engine organizes tools into categories defined in `ToolCategory`:
- `OBSERVABILITY` -- Trace, log, metric queries
- `ANALYSIS` -- Pure analysis functions
- `ORCHESTRATION` -- Sub-agent coordination
- `INFRASTRUCTURE` -- GKE, compute resources
- `ALERTING` -- Alert policies
- `REMEDIATION` -- Suggestions, risk assessment
- `MEMORY` -- Memory bank operations
- `DISCOVERY` -- Resource discovery
- `MUTATION` -- Write operations (restarts, scaling)

Each tool has a `ToolPolicy` with access level, category, description, risk level, and whether project context is required. The `PolicyDecision` schema (Pydantic, `frozen=True, extra="forbid"`) carries the decision result.

> **Experimental Notice**: As of February 2026, the Policy Engine is running in **Audit-Only / Lenient Mode**. Rejections based on missing project context or restricted categories are currently logging warnings instead of blocking, to gather telemetry on tool usage. Admin-level tools trigger a Human Approval request rather than outright rejection.

### 7. Additional Core Components

The `sre_agent/core/` directory contains several additional components that support the autonomous architecture:

| Module | Purpose |
| :--- | :--- |
| `runner_adapter.py` | Runner adaptation layer for different execution modes |
| `model_callbacks.py` | Cost/token tracking and budget enforcement callbacks |
| `tool_callbacks.py` | Tool output truncation and post-processing |
| `large_payload_handler.py` | Large result set handling with sandbox offload |
| `router.py` | Request routing logic (`route_request` function) |

---

## Implementation Status

### Phase 1: Core Infrastructure -- Complete
1. `Runner` class with stateless execution cycle
2. Three-tier `PromptComposer` with `DomainContext` and `SessionSummary`
3. `ContextCompactor` with Sliding Window and `CompactionConfig`
4. `Summarizer` service for event summarization

### Phase 2: Safety Layer -- Complete
1. `PolicyEngine` with tool classification (`ToolAccessLevel`, `ToolCategory`)
2. `HumanApprovalEvent` workflow (`sre_agent/core/approval.py`)
3. All existing tools categorized as RO/RW with `TOOL_POLICIES` registry

### Phase 3: Knowledge Graph -- Complete
1. `GraphService` for dependency mapping with `ServiceType` and `EdgeType` enums
2. Integration with trace analysis via `build_service_dependency_graph` tool
3. Blast radius calculation with `analyze_upstream_downstream_impact` tool

### Phase 4: Integration -- Complete
1. Components wired into the agent via `sre_agent/agent.py`
2. Comprehensive tests in `tests/unit/sre_agent/core/`
3. Documentation updated

---

## File Structure

```
sre_agent/
+-- core/                          # Core autonomous reliability components
|   +-- __init__.py
|   +-- runner.py                  # Stateless execution harness (RunnerConfig)
|   +-- runner_adapter.py          # Runner adaptation layer
|   +-- prompt_composer.py         # Three-tier prompt composition (DomainContext, SessionSummary)
|   +-- context_compactor.py       # Sliding window context management (CompactionConfig, WorkingContext)
|   +-- summarizer.py              # Event summarization service
|   +-- policy_engine.py           # Safety interception layer (ToolPolicy, PolicyDecision)
|   +-- approval.py                # Human-in-the-loop workflow (ApprovalManager)
|   +-- graph_service.py           # Dependency knowledge graph (DependencyNode, DependencyEdge)
|   +-- circuit_breaker.py         # Three-state failure recovery (CLOSED/OPEN/HALF_OPEN)
|   +-- model_callbacks.py         # Cost/token tracking, budget enforcement
|   +-- tool_callbacks.py          # Tool output truncation and post-processing
|   +-- large_payload_handler.py   # Large result set handling (sandbox offload)
|   +-- router.py                  # Request routing logic
+-- schema.py                      # Pydantic models (InvestigationPhase, etc.)
+-- agent.py                       # Main orchestrator using Runner
+-- ...
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Context Efficiency | <32K tokens per turn | Token counter |
| Zero-Downtime Restart | <100ms context reconstruction | Latency measurement |
| Safety Compliance | 100% write operations approved | Audit log |
| Graph Coverage | >80% services mapped | Graph metrics |

---

## References

- [Codex Pattern](https://github.com/openai/codex): Unrolled execution model
- [Google ADK](https://github.com/google/adk-python): Agent Development Kit
- [OODA Loop](https://en.wikipedia.org/wiki/OODA_loop): Decision cycle framework

---

*Last verified: 2026-02-21
