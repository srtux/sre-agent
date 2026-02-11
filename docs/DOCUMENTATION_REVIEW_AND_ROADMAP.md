# Documentation Review & Future Roadmap

**Date**: 2026-02-11
**Scope**: Full audit of 61+ documentation files, cross-referenced against codebase

---

## Part 1: Documentation Audit Findings

### 1.1 Date Staleness

All documents should reflect the same "last verified" date when they are in sync. Currently:

| Document | Last Verified | Status |
|----------|--------------|--------|
| `CLAUDE.md` | 2026-02-11 | Current |
| `AGENTS.md` | 2026-02-02 | **9 days stale** |
| `README.md` | 2026-02-02 | **9 days stale** |
| `docs/README.md` | 2026-02-02 | **9 days stale** |
| `docs/PROJECT_PLAN.md` | 2026-02-07 | **4 days stale** |

**Action**: Update all "Last verified" dates to 2026-02-11 after corrections are applied.

---

### 1.2 Factual Discrepancies Found

#### D1: Panel Count Mismatch in PROJECT_PLAN.md
- **Location**: `docs/PROJECT_PLAN.md` line 80
- **Says**: "Four parallel specialist panels (Trace, Metrics, Logs, Alerts)"
- **Reality**: 5 panels exist in `council/panels.py` — Trace, Metrics, Logs, Alerts, **Data** (BigQuery/CA)
- **CLAUDE.md and llm.txt**: Correctly state "5 specialist panel factories"
- **Severity**: Medium — PROJECT_PLAN.md contradicts the codebase and other docs

#### D2: Preferences Router Missing from CLAUDE.md
- **Location**: `CLAUDE.md` routers list
- **Says**: "HTTP handlers: agent, sessions, tools, health, system, permissions, help"
- **Reality**: `sre_agent/api/routers/preferences.py` also exists
- **llm.txt**: Correctly lists "preferences" in the routers line
- **Severity**: Low — minor omission

#### D3: BigQuery Playbook Not Documented
- **Location**: `CLAUDE.md` playbooks description
- **Says**: "Runbook execution (GKE, Cloud Run, SQL, Pub/Sub, GCE)"
- **Reality**: `sre_agent/tools/playbooks/bigquery.py` also exists
- **Severity**: Low

#### D4: agent_debugger Sub-Agent Not Documented
- **Location**: `CLAUDE.md` sub_agents listing
- **Says**: trace.py, logs.py, metrics.py, alerts.py, root_cause.py
- **Reality**: `sre_agent/sub_agents/agent_debugger.py` also exists
- **Severity**: Low

#### D5: Test Count Discrepancy Between CLAUDE.md and PROJECT_PLAN.md
- **CLAUDE.md**: "1909+ tests passing"
- **PROJECT_PLAN.md**: "1989 backend tests, 129 Flutter tests passing" (from Phase 3.5)
- **Severity**: Medium — CLAUDE.md reports an earlier count

#### D6: Architecture Docs Missing from docs/README.md Index
- **Missing from index**: `docs/architecture/help_system.md`, `docs/architecture/AGENTS_AND_TOOLS.md`, `docs/architecture/system_instruction_snapshot_v1.md`
- **Severity**: Low — docs exist but are not discoverable from the index

#### D7: Guide Docs Missing from docs/README.md Index
- **Missing from Guides section**: `docs/guides/dashboard_ui.md`, `docs/guides/frontend_testing.md`, `docs/guides/project_selector.md`
- **Severity**: Medium — three complete guides are invisible to readers navigating via the index

#### D8: Test File Count in llm.txt
- **Location**: `llm.txt` line 102
- **Says**: "Test suite (~138 files)"
- **Reality**: 189 Python test files found, plus 23 Flutter test files
- **Severity**: Low — understated

#### D9: Coverage Target Inconsistency in AGENTS.md
- **AGENTS.md** line 644: "Target: 100% test coverage. Every branch and error condition must be verified."
- **AGENTS.md** line 5 (Quick Rules): "80% minimum gate; aim for 100% on new tools"
- **pyproject.toml**: `--cov-fail-under=80`
- **Severity**: Low — line 644 overstates; quick rules and pyproject are consistent

#### D10: AGENTS.md Core Components Tree Incomplete
- **Location**: `AGENTS.md` line 56-68 (Core Components tree)
- **Missing**: `council/`, `core/`, `memory/`, `models/`, `resources/` directories
- **CLAUDE.md**: Lists all directories correctly
- **Severity**: Medium — AGENTS.md tree is significantly simplified vs reality

#### D11: llm.txt Missing Key Patterns
- **Missing from llm.txt**: Session persistence stale closure pattern (CRITICAL in AGENTS.md Section 5), Sandbox code execution (AGENTS.md Section 13), Circuit breaker, Model callbacks
- **Severity**: Low-Medium — llm.txt is intentionally concise, but the session persistence pattern is marked CRITICAL

#### D12: README.md Architecture Diagram Outdated
- **Location**: `README.md` Mermaid diagram (lines 45-68)
- **Issue**: Shows only 3 "Core Squad" members (Trace, Log, RCA) — missing Metrics Analyst, Alerts Analyst, and the entire Council architecture
- **Severity**: Medium — the public-facing diagram doesn't reflect current architecture

---

### 1.3 Structural & Organizational Issues

| Issue | Description |
|-------|-------------|
| **No CHANGELOG** | No CHANGELOG.md exists. PROJECT_PLAN.md acts as both roadmap and changelog, making it harder to find release-specific changes. |
| **Duplicate information** | Tool registration checklist exists in CLAUDE.md (10 steps), AGENTS.md (10 steps, slightly different order), and implicitly in llm.txt. A single canonical checklist with cross-references would reduce drift. |
| **No API versioning docs** | The API reference (`docs/reference/api.md`) does not mention versioning strategy. As the API evolves, breaking changes could impact frontend compatibility. |
| **Missing contribution guide** | No CONTRIBUTING.md for external contributors. AGENTS.md serves this role for AI agents but not for human contributors. |
| **eval/ files not indexed** | PROJECT_PLAN.md mentions 9 eval scenarios across 3 files, but the actual eval/ directory has 9 test JSON files. The eval/README.md should be updated. |

---

## Part 2: Improvement Suggestions for the Agentic Application

### 2.1 Agent Architecture Improvements

#### I1: Adaptive Panel Selection (Council 2.0)
**Current state**: The `IntentClassifier` uses rule-based keyword matching to select investigation mode (Fast/Standard/Debate).
**Improvement**: Replace or augment with an LLM-based classifier that considers:
- Historical investigation patterns from memory
- Current incident severity from alert metadata
- Resource availability (token budget remaining)

This would reduce misclassifications where keyword overlap causes wrong panel dispatch.

#### I2: Streaming Panel Results
**Current state**: In Standard mode, all 5 panels must complete before the Synthesizer runs.
**Improvement**: Implement progressive synthesis — the Synthesizer starts working as soon as the first 2-3 panels complete, then refines as remaining panels finish. This reduces perceived latency for users waiting on investigations.

#### I3: Panel Self-Assessment & Dynamic Re-Dispatch
**Current state**: Panels run once and report findings.
**Improvement**: Add a confidence-aware feedback loop where:
1. Each panel returns a confidence score with its findings
2. If a panel reports low confidence (<0.3), the orchestrator can re-dispatch it with refined queries
3. If two panels contradict each other, automatically escalate to Debate mode

#### I4: Tool Usage Analytics
**Current state**: `model_callbacks.py` tracks token usage and cost.
**Improvement**: Add tool-level analytics:
- Track which tools are most/least used per investigation type
- Identify tools that frequently error or timeout
- Feed analytics back into prompt optimization (drop rarely-used tools from context)

#### I5: Investigation Templates
**Current state**: Every investigation starts from scratch with the system prompt.
**Improvement**: Pre-built investigation templates for common scenarios:
- "High latency in service X" → Pre-configure metrics queries, trace filters
- "Error rate spike" → Pre-configure log patterns, alert timeline
- "Deployment regression" → Pre-configure change correlation, before/after comparison

Templates would reduce tool calls and token usage by 30-50% for common patterns.

---

### 2.2 Reliability & Resilience Improvements

#### I6: Circuit Breaker Observability Dashboard
**Current state**: Circuit breaker exists (`core/circuit_breaker.py`) with three states.
**Improvement**: Expose circuit breaker state to the Flutter dashboard so users can see:
- Which GCP APIs are currently degraded (OPEN state)
- Historical failure rates per API
- Time to recovery estimates

#### I7: Token Budget Forecasting
**Current state**: `model_callbacks.py` enforces a hard token budget limit.
**Improvement**: Add predictive budget management:
- Estimate remaining token cost before starting each panel
- If budget is projected to be exceeded, downgrade from Debate to Standard, or Standard to Fast
- Surface budget warnings in the UI before hard cutoff

#### I8: Graceful Degradation Hierarchy
**Current state**: MCP fails → Direct API fallback (binary).
**Improvement**: Multi-level degradation:
1. Full MCP (rich SQL analysis)
2. Simplified MCP (reduced query complexity)
3. Direct API (basic fetches)
4. Cached results (stale but available)
5. Synthetic estimates (ML-based approximation)

#### I9: Rate Limiting & Request Queuing
**Current state**: Identified as a follow-up item in PROJECT_PLAN.md but not implemented.
**Improvement**: Implement `slowapi` middleware with:
- Per-user rate limits (prevent single user from consuming all resources)
- Per-endpoint limits (protect expensive query endpoints)
- Request queuing for burst traffic instead of hard rejection

---

### 2.3 User Experience Improvements

#### I10: Investigation History & Replay
**Current state**: Sessions persist but past investigations are not easily reviewable.
**Improvement**: Add an "Investigation History" panel showing:
- Past investigations with timestamps and outcomes
- Ability to replay an investigation against current data
- Diff view: "What changed since last investigation?"

#### I11: Natural Language Query Builder
**Current state**: Manual query bars require MQL/Cloud Logging filter syntax.
**Improvement**: Add NL-to-query translation:
- User types "CPU usage above 80% in the last hour"
- Agent translates to `metric.type="compute.googleapis.com/instance/cpu/utilization" AND value.double_value > 0.8`
- Show generated query for user learning

#### I12: Collaborative Investigations
**Current state**: Single-user sessions.
**Improvement**: Support multi-user investigation sessions:
- Share investigation link with team
- Real-time cursors showing who is looking at what
- Comments and annotations on findings
- Escalation workflow: SRE → Manager → Incident Commander

#### I13: Mobile-Responsive Dashboard
**Current state**: Flutter Web optimized for desktop.
**Improvement**: Add responsive breakpoints for tablet/mobile:
- Collapsible sidebar for panel navigation
- Swipeable panel cards on mobile
- Push notifications for critical alert findings

---

### 2.4 Intelligence & Learning Improvements

#### I14: Cross-Incident Knowledge Graph
**Current state**: Memory bank stores individual investigation patterns.
**Improvement**: Build a persistent knowledge graph:
- Nodes: Services, APIs, error types, deployment events
- Edges: "caused by", "correlated with", "resolved by"
- Automatically populated from investigation findings
- Queryable: "What usually causes checkout-service latency?"

#### I15: Proactive Anomaly Detection
**Current state**: Agent is reactive — investigates when asked.
**Improvement**: Background monitoring mode:
- Continuously poll key SLO metrics
- Run lightweight anomaly detection (Z-score, seasonal decomposition)
- Surface pre-incident warnings: "Error budget burn rate suggests SLO violation in ~4 hours"
- Auto-create investigation when thresholds are breached

#### I16: Investigation Quality Scoring
**Current state**: Evals run in CI but results aren't surfaced to users.
**Improvement**: Post-investigation quality report:
- Signal coverage: "This investigation examined 3/4 signal types"
- Confidence score: Aggregate of all panel confidences
- Evidence strength: How many data points support the conclusion
- Suggestions: "Consider also checking audit logs for recent deployments"

#### I17: Fine-Tuned Prompt Optimization
**Current state**: Static system prompts with some dynamic composition.
**Improvement**: Implement prompt A/B testing:
- Track investigation quality metrics per prompt variant
- Automatically select higher-performing prompts
- Use few-shot examples from successful past investigations (RAG from memory bank)

---

### 2.5 Operational & DevOps Improvements

#### I18: Canary Deployment for Agent Changes
**Current state**: `deploy_all.py` does full-stack deployment.
**Improvement**: Add canary deployment pipeline:
- Deploy new agent version to 5% of traffic
- Run automated eval suite against canary
- Compare quality metrics (confidence, tool errors, token usage)
- Auto-promote or rollback based on metrics

#### I19: Cost Attribution & Chargeback
**Current state**: Token usage tracked but not attributed.
**Improvement**: Per-team/per-project cost tracking:
- Track LLM token cost per GCP project investigated
- Track GCP API call costs per investigation
- Monthly cost reports per team
- Budget alerts when team approaches spending limit

#### I20: Automated Documentation Generation
**Current state**: Docs are manually maintained (61+ files).
**Improvement**: Auto-generate parts of documentation:
- Tool catalog (`docs/reference/tools.md`) from `@adk_tool` docstrings
- API reference from FastAPI OpenAPI spec
- Configuration reference from `.env.example` + code analysis
- Architecture diagrams from import analysis

---

## Part 3: Proposed Roadmap

### Phase 4: Intelligent Automation (Q1 2026)

**Theme**: From reactive investigation to proactive intelligence.

| Priority | Item | Category | Complexity | Dependencies |
|----------|------|----------|------------|--------------|
| P0 | Fix all documentation discrepancies (D1-D12) | Docs | Low | None |
| P0 | Rate limiting middleware (I9) | Reliability | Medium | `slowapi` |
| P0 | CORS tightening (from audit follow-ups) | Security | Low | None |
| P1 | Token budget forecasting (I7) | Reliability | Medium | model_callbacks.py |
| P1 | Investigation templates (I5) | UX/Intelligence | Medium | prompt_composer.py |
| P1 | Streaming panel results (I2) | Architecture | High | council/orchestrator.py |
| P1 | Tool usage analytics (I4) | Operations | Medium | model_callbacks.py |
| P2 | Circuit breaker dashboard (I6) | UX | Low | Flutter dashboard |
| P2 | NL query builder (I11) | UX | Medium | Explorer query bar |
| P2 | Automated doc generation (I20) | DevOps | Medium | CI pipeline |

### Phase 5: Proactive SRE (Q2 2026)

**Theme**: The agent anticipates problems before users ask.

| Priority | Item | Category | Complexity | Dependencies |
|----------|------|----------|------------|--------------|
| P0 | Proactive anomaly detection (I15) | Intelligence | High | Background workers, SLO tools |
| P0 | Cross-incident knowledge graph (I14) | Intelligence | High | Memory bank, Firestore |
| P1 | Adaptive panel selection (I1) | Architecture | Medium | Intent classifier |
| P1 | Panel self-assessment & re-dispatch (I3) | Architecture | High | Council orchestrator |
| P1 | Investigation quality scoring (I16) | Intelligence | Medium | Eval framework |
| P2 | Investigation history & replay (I10) | UX | Medium | Session service |
| P2 | Graceful degradation hierarchy (I8) | Reliability | Medium | MCP fallback |
| P2 | Cost attribution (I19) | Operations | Medium | model_callbacks.py |

### Phase 6: Enterprise & Scale (Q3-Q4 2026)

**Theme**: Multi-team, multi-cloud, production-grade governance.

| Priority | Item | Category | Complexity | Dependencies |
|----------|------|----------|------------|--------------|
| P0 | Confirmation Bridge / HITL 2.0 (from PROJECT_PLAN Phase 4) | Safety | High | Policy engine |
| P0 | Zero-Trust Identity propagation (from PROJECT_PLAN Phase 4) | Security | High | Auth system |
| P1 | Collaborative investigations (I12) | UX | High | WebSocket, session sharing |
| P1 | Canary deployment pipeline (I18) | DevOps | High | Cloud Build |
| P1 | Prompt A/B testing (I17) | Intelligence | Medium | Eval framework |
| P2 | Mobile-responsive dashboard (I13) | UX | Medium | Flutter responsive |
| P2 | Chaos Engineering Sub-Agent (from PROJECT_PLAN) | Intelligence | High | Runbook automation |
| P2 | Multi-cloud support (AWS CloudWatch, Azure Monitor) | Architecture | Very High | New client factories |

### Quick Wins (Can Be Done Immediately)

These items have low complexity and high impact:

1. **Fix D1-D12 documentation discrepancies** — Synchronize all docs
2. **Add missing guides to docs/README.md index** — 3 guides are invisible
3. **Update README.md Mermaid diagram** — Reflect Council architecture
4. **Add CORS explicit allowlist** — Security hardening
5. **Replace `time.sleep()` in tests with `freezegun`** — Test quality
6. **Add `CONTRIBUTING.md`** — Lower barrier for new contributors
7. **Create `CHANGELOG.md`** — Separate release tracking from roadmap

---

## Part 4: Documentation Fix Recommendations

Below is the specific list of edits needed to bring all documentation into sync:

### Fix F1: `docs/PROJECT_PLAN.md` line 80
Change "Four parallel specialist panels (Trace, Metrics, Logs, Alerts)" to "Five parallel specialist panels (Trace, Metrics, Logs, Alerts, Data)"

### Fix F2: `CLAUDE.md` routers list
Add "preferences" to the routers list: "HTTP handlers: agent, sessions, tools, health, system, permissions, preferences, help"

### Fix F3: `CLAUDE.md` playbooks description
Change "(GKE, Cloud Run, SQL, Pub/Sub, GCE)" to "(GKE, Cloud Run, SQL, Pub/Sub, GCE, BigQuery)"

### Fix F4: `CLAUDE.md` sub_agents listing
Add agent_debugger.py to the sub-agents list

### Fix F5: `CLAUDE.md` test count
Update "1909+ tests passing" to "1989+ backend tests, 129 Flutter tests passing"

### Fix F6: `docs/README.md` Architecture section
Add entries for help_system.md, AGENTS_AND_TOOLS.md, system_instruction_snapshot_v1.md

### Fix F7: `docs/README.md` Guides section
Add entries for dashboard_ui.md, frontend_testing.md, project_selector.md

### Fix F8: `llm.txt` line 102
Update "~138 files" to "~210+ files"

### Fix F9: `AGENTS.md` line 644
Clarify: "Target: 80% minimum gate on all code. 100% coverage target on new tools and core logic."

### Fix F10: `AGENTS.md` Core Components tree
Add council/, core/, memory/, models/, resources/ directories to the tree

### Fix F11: `README.md` Mermaid diagram
Update to include Council of Experts architecture with 5 panels

### Fix F12: Update all "Last verified" dates
Set all documents to 2026-02-11 after corrections are applied

---

*Generated: 2026-02-11 — Documentation Review & Roadmap*
