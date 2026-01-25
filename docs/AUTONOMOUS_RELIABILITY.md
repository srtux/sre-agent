# Autonomous Reliability Architecture

**Status**: Implementation In Progress
**Last Updated**: 2026-01-25
**Author**: Architecture Team

---

## Overview

This document describes the architectural refactoring of the SRE Agent from a standard "prompt-response" loop to a **Stateful, Event-Driven Harness** based on the "Unrolled Codex" pattern and Google's Agent Development Kit (ADK).

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
┌─────────────────────────────────────────────────────────────────────────────┐
│                           THE UNROLLED EXECUTION MODEL                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐     ┌──────────────────┐     ┌────────────────────┐   │
│  │   User Request   │ ──► │     Runner       │ ──► │   LLM Response     │   │
│  │   (External)     │     │   (Harness)      │     │   (Intent Only)    │   │
│  └──────────────────┘     └──────────────────┘     └────────────────────┘   │
│                                   │                          │               │
│                                   ▼                          ▼               │
│                          ┌────────────────┐         ┌────────────────┐       │
│                          │ Session Store  │ ◄───────│ Policy Engine  │       │
│                          │ (Event Log)    │         │ (Intercept)    │       │
│                          └────────────────┘         └────────────────┘       │
│                                                              │               │
│                                                              ▼               │
│                                                     ┌────────────────┐       │
│                                                     │ Tool Executor  │       │
│                                                     │ (Safe Execute) │       │
│                                                     └────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- **No Internal Memory Loops**: Remove any `while True:` inside LLM logic
- **Stateless Execution**: Each turn reconstructs context from event log
- **External Loop Control**: The Runner manages the execution cycle

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
- Follow the OODA loop: Observe → Orient → Decide → Act

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

### 3. Context Engineering (Sliding Window)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONTEXT COMPACTION STRATEGY                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Full Event Log (Persisted)                                                  │
│  ├─ Event 1: UserMessage("Investigate latency spike")                       │
│  ├─ Event 2: ModelThought("Starting aggregate analysis")                    │
│  ├─ Event 3: ToolOutput(analyze_aggregate_metrics → 50KB JSON)              │
│  ├─ Event 4: ToolOutput(fetch_trace → 20KB trace data)                      │
│  ├─ Event 5: ModelThought("Found bottleneck in db-service")                 │
│  ├─ ...                                                                      │
│  └─ Event N: UserMessage("What about the logs?")                            │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                     CONTEXT COMPACTION                              │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │                                                                      │     │
│  │  Working Context (Sent to LLM):                                      │     │
│  │  ┌──────────────────────────────────────────────────────────────┐   │     │
│  │  │ SUMMARY (Compacted from Events 1-N-5):                        │   │     │
│  │  │ - User asked about latency spike in checkout-service          │   │     │
│  │  │ - Aggregate analysis found db-service as bottleneck           │   │     │
│  │  │ - Trace abc123 shows 1.2s delay in database-proxy span        │   │     │
│  │  │ - 4 log patterns identified: 2 errors, 2 warnings             │   │     │
│  │  └──────────────────────────────────────────────────────────────┘   │     │
│  │  ┌──────────────────────────────────────────────────────────────┐   │     │
│  │  │ RECENT RAW EVENTS (Events N-4 to N):                          │   │     │
│  │  │ [Full content of last 5 events]                               │   │     │
│  │  └──────────────────────────────────────────────────────────────┘   │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Compaction Rules:**
1. **Token Budget**: Keep working context under 32K tokens
2. **Summarizer Trigger**: When raw events exceed 24K tokens
3. **Summary Retention**: Summaries are stored as `CompactionEvent` in the log
4. **Recency Bias**: Last 5 events always sent in full

### 4. The Reasoning Engine (OODA Loop)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OODA REASONING LOOP                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐    │
│  │  OBSERVE   │ ──► │   ORIENT   │ ──► │   DECIDE   │ ──► │    ACT     │    │
│  │            │     │            │     │            │     │            │    │
│  │ Gather     │     │ Map to     │     │ Form       │     │ Execute    │    │
│  │ Telemetry  │     │ Knowledge  │     │ Hypothesis │     │ Synthetic  │    │
│  │ Signals    │     │ Graph      │     │            │     │ Test       │    │
│  └────────────┘     └────────────┘     └────────────┘     └────────────┘    │
│        │                  │                  │                  │            │
│        ▼                  ▼                  ▼                  ▼            │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                         EVALUATE                                    │     │
│  │                                                                      │     │
│  │  - Did the test confirm or refute the hypothesis?                   │     │
│  │  - Update confidence scores in the Knowledge Graph                  │     │
│  │  - If refuted, return to OBSERVE with new constraints               │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5. GraphService (Dependency Mapping)

```python
@dataclass
class DependencyNode:
    """A node in the service dependency graph."""
    service_name: str
    service_type: ServiceType  # COMPUTE, DATABASE, CACHE, QUEUE, EXTERNAL
    metadata: dict[str, Any]

@dataclass
class DependencyEdge:
    """An edge representing a dependency between services."""
    source: str
    target: str
    edge_type: EdgeType  # CALLS, READS_FROM, WRITES_TO, SUBSCRIBES
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

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           POLICY ENGINE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Tool Call Intent                                                            │
│       │                                                                      │
│       ▼                                                                      │
│  ┌────────────────┐                                                          │
│  │ Classification │─────────────────────────────────────────┐               │
│  │ RO / RW / ADMIN│                                         │               │
│  └────────────────┘                                         │               │
│       │                                                      │               │
│       ├─── READ_ONLY ───► Execute Immediately               │               │
│       │                                                      │               │
│       ├─── WRITE ────────► ┌────────────────────────────┐   │               │
│       │                    │ Human Approval Required     │   │               │
│       │                    │                             │   │               │
│       │                    │ Emit: HumanApprovalEvent   │   │               │
│       │                    │ Pause: Execution Loop      │   │               │
│       │                    │ Wait:  HumanApproval       │   │               │
│       │                    └────────────────────────────┘   │               │
│       │                             │                        │               │
│       │                             ▼                        │               │
│       │                    ┌────────────────────────────┐   │               │
│       │                    │ Approval Received?         │   │               │
│       │                    │ YES: Execute with audit    │   │               │
│       │                    │ NO:  Return rejection      │   │               │
│       │                    └────────────────────────────┘   │               │
│       │                                                      │               │
│       └─── ADMIN ────────► Reject (Not Allowed)             │               │
│                                                              │               │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Tool Classification:**

| Category | Access | Examples | Approval |
|----------|--------|----------|----------|
| READ_ONLY | RO | `fetch_trace`, `list_logs`, `query_promql` | Auto |
| WRITE | RW | `restart_pod`, `scale_deployment` | Human Required |
| ADMIN | RESTRICTED | `delete_resource`, `modify_iam` | Rejected |

---

## Implementation Plan

### Phase 1: Core Infrastructure
1. ✅ Create `Runner` class with stateless execution cycle
2. ✅ Implement three-tier `PromptComposer`
3. ✅ Add `ContextCompactor` with Sliding Window
4. ✅ Create `Summarizer` service

### Phase 2: Safety Layer
1. ✅ Implement `PolicyEngine` with tool classification
2. ✅ Add `HumanApprovalEvent` workflow
3. ✅ Categorize all existing tools as RO/RW

### Phase 3: Knowledge Graph
1. ✅ Create `GraphService` for dependency mapping
2. ✅ Integrate with trace analysis
3. ✅ Add blast radius calculation

### Phase 4: Integration
1. ✅ Wire new components into existing agent
2. ✅ Add comprehensive tests
3. ✅ Update documentation

---

## File Structure

```
sre_agent/
├── core/                          # NEW: Core autonomous reliability components
│   ├── __init__.py
│   ├── runner.py                  # Stateless execution harness
│   ├── prompt_composer.py         # Three-tier prompt composition
│   ├── context_compactor.py       # Sliding window context management
│   ├── summarizer.py              # Event summarization service
│   ├── policy_engine.py           # Safety interception layer
│   ├── approval.py                # Human-in-the-loop workflow
│   └── graph_service.py           # Dependency knowledge graph
├── schema.py                      # Updated with new event types
├── agent.py                       # Updated to use Runner
└── ...
```

---

## Migration Strategy

1. **Parallel Operation**: New components run alongside existing code
2. **Feature Flags**: `USE_AUTONOMOUS_RUNNER=true` enables new path
3. **Gradual Rollout**: Start with read-only operations
4. **Validation**: Compare outputs between old and new paths

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
- [Google ADK](https://github.com/googleapis/python-genai): Agent Development Kit
- [OODA Loop](https://en.wikipedia.org/wiki/OODA_loop): Decision cycle framework
