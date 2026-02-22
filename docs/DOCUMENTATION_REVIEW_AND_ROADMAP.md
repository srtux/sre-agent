# Documentation Review & Future Roadmap

**Date**: 2026-02-15 (updated from 2026-02-11 original review)
**Scope**: Full audit of 61+ documentation files, cross-referenced against codebase

---

## Part 1: Documentation Audit Findings

### 1.1 Date Staleness

All documents should reflect the same "last verified" date when they are in sync. Current status as of 2026-02-15:

| Document | Last Verified | Status |
|----------|--------------|--------|
| `CLAUDE.md` | 2026-02-15 | **Current** |
| `AGENTS.md` | 2026-02-11 | 4 days stale |
| `README.md` | 2026-02-11 | 4 days stale |
| `docs/README.md` | 2026-02-15 | **Current** |
| `docs/PROJECT_PLAN.md` | 2026-02-07 | 8 days stale |
| `docs/OBSERVABILITY.md` | 2026-02-15 | **Current** (updated in this review) |
| `docs/reference/configuration.md` | 2026-02-15 | **Current** |
| `docs/architecture/system_overview.md` | 2026-02-15 | **Current** |
| `docs/EVALUATIONS.md` | 2026-02-15 | **Current** |
| `docs/guides/development.md` | 2026-02-15 | **Current** |
| `docs/guides/getting_started.md` | 2026-02-15 | **Current** |
| `docs/testing/linting.md` | 2026-02-15 | **Current** |
| `docs/concepts/online_research_and_self_healing.md` | 2026-02-14 | 1 day stale |
| `docs/reference/api.md` | 2026-02-02 | **13 days stale** |
| `docs/reference/tools.md` | 2026-02-02 | **13 days stale** |
| `docs/reference/security.md` | 2026-02-02 | **13 days stale** |
| `docs/testing/testing.md` | 2026-02-02 | **13 days stale** |

**Action**: Update all "Last verified" dates to 2026-02-15 after corrections are applied.

---

### 1.2 Factual Discrepancies Found

#### D1: Panel Count Mismatch in PROJECT_PLAN.md -- PARTIALLY FIXED
- **Location**: `docs/PROJECT_PLAN.md` line 80, line 84
- **Line 80**: Fixed -- now correctly says "Five parallel specialist panels"
- **Line 84**: Still says "Four parallel panels followed by synthesizer merge"
- **Status**: Remaining issue on line 84 should be updated to "Five parallel panels"

#### D2: Preferences Router Missing from CLAUDE.md -- FIXED
- **Location**: `CLAUDE.md` routers list
- **Status**: Fixed -- now lists "agent, sessions, tools, health, system, permissions, preferences, help"

#### D3: BigQuery Playbook Not Documented -- FIXED
- **Location**: `CLAUDE.md` playbooks description
- **Status**: Fixed -- now says "(GKE, Cloud Run, SQL, Pub/Sub, GCE, BigQuery)"

#### D4: agent_debugger Sub-Agent Not Documented -- FIXED
- **Location**: `CLAUDE.md` sub_agents listing
- **Status**: Fixed -- `agent_debugger.py` now listed

#### D5: Test Count Discrepancy -- FIXED
- **CLAUDE.md**: Now says "2277+ backend tests, 129 Flutter tests passing"
- **Status**: Updated to current counts

#### D6: Architecture Docs Missing from docs/README.md Index -- FIXED
- **Status**: Fixed -- `help_system.md`, `AGENTS_AND_TOOLS.md`, and `system_instruction_snapshot_v1.md` now in index

#### D7: Guide Docs Missing from docs/README.md Index -- FIXED
- **Status**: Fixed -- `dashboard_ui.md`, `frontend_testing.md`, and `project_selector.md` now in Guides section

#### D8: Test File Count in llm.txt -- FIXED
- **Status**: Fixed -- now says "~210+ files"

#### D9: Coverage Target Inconsistency in AGENTS.md
- **Status**: Not yet resolved. AGENTS.md line 644 still overstates target.
- **Recommended fix**: Clarify "80% minimum gate on all code. 100% coverage target on new tools and core logic."

#### D10: AGENTS.md Core Components Tree Incomplete
- **Status**: Not yet resolved. Tree is still simplified vs reality.
- **Recommended fix**: Add `council/`, `core/`, `memory/`, `models/`, `resources/` directories

#### D11: llm.txt Missing Key Patterns
- **Status**: Partially addressed. Test file count updated, but session persistence stale closure pattern, sandbox code execution, circuit breaker, and model callbacks still not documented in llm.txt.

#### D12: README.md Architecture Diagram Outdated
- **Status**: Not yet resolved. Mermaid diagram still does not reflect Council architecture.

---

### 1.3 New Discrepancies Found (2026-02-15 Review)

#### D13: Self-Healing Playbook Not in CLAUDE.md Playbooks List
- **Location**: `CLAUDE.md` playbooks description
- **Says**: "(GKE, Cloud Run, SQL, Pub/Sub, GCE, BigQuery)"
- **Reality**: `sre_agent/tools/playbooks/self_healing.py` also exists
- **Severity**: Low

#### D14: Spanner Troubleshooting Playbook Not Implemented in Code
- **Location**: `docs/SPANNER_TROUBLESHOOTING_PLAYBOOK.md`
- **Issue**: The doc describes a comprehensive Spanner playbook, but there is no `sre_agent/tools/playbooks/spanner.py` file. Spanner is listed as a planned category in `tools/playbooks/__init__.py` but not yet implemented.
- **Severity**: Medium -- doc exists but no corresponding code playbook

#### D15: PROJECT_PLAN.md Line 84 Still Says "Four"
- **Location**: `docs/PROJECT_PLAN.md` line 84
- **Says**: "Four parallel panels followed by synthesizer merge"
- **Reality**: 5 panels (Trace, Metrics, Logs, Alerts, Data)
- **Severity**: Medium

#### D16: Research Tools and GitHub Tools Not in CLAUDE.md tools/ Listing
- **Location**: `CLAUDE.md` codebase structure
- **Issue**: The tools/ tree already lists `research.py` and `github/` but the descriptions in the environment variables section are incomplete. `GOOGLE_CUSTOM_SEARCH_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` are now documented.
- **Severity**: Low -- mostly addressed

#### D17: Dashboard Query Language Features Undocumented
- **Location**: No dedicated documentation exists
- **Reality**: Flutter dashboard now has query language support including:
  - `query_autocomplete_overlay.dart` -- autocomplete for queries
  - `query_helpers.dart` -- query helper functions
  - `query_language_badge.dart` -- visual badge showing query language
  - `query_language_toggle.dart` -- toggle between query languages
  - `manual_query_bar.dart` -- manual query input
  - NL-to-query routing via `explorer_query_service.dart`
- **Severity**: Medium -- significant feature with no documentation

#### D18: OBSERVABILITY.md Missing Dashboard Query and Langfuse Session Features
- **Location**: `docs/OBSERVABILITY.md`
- **Issue**: Does not mention Langfuse session/user grouping, OTel context bridging, or the `RUNNING_IN_AGENT_ENGINE` env var.
- **Status**: Fixed in this review cycle.

---

### 1.3 Structural & Organizational Issues

| Issue | Description | Status |
|-------|-------------|--------|
| **No CHANGELOG** | No CHANGELOG.md exists. PROJECT_PLAN.md acts as both roadmap and changelog. | Open |
| **Duplicate information** | Tool registration checklist in CLAUDE.md, AGENTS.md, and llm.txt. | Open |
| **No API versioning docs** | `docs/reference/api.md` does not mention versioning strategy. | Open |
| **Missing contribution guide** | No CONTRIBUTING.md for external contributors. | Open |
| **eval/ files not indexed** | eval/ directory has 9+ test JSON files; eval/README.md should be updated. | Open |
| **New: Online research docs** | `docs/concepts/online_research_and_self_healing.md` added but not linked from all indexes. | Partially addressed |

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
**Improvement**: Implement progressive synthesis -- the Synthesizer starts working as soon as the first 2-3 panels complete, then refines as remaining panels finish. This reduces perceived latency for users waiting on investigations.

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

**Progress**: Global tool error learning has been implemented in `memory/` which partially addresses tool error tracking.

#### I5: Investigation Templates
**Current state**: Every investigation starts from scratch with the system prompt.
**Improvement**: Pre-built investigation templates for common scenarios:
- "High latency in service X" -- Pre-configure metrics queries, trace filters
- "Error rate spike" -- Pre-configure log patterns, alert timeline
- "Deployment regression" -- Pre-configure change correlation, before/after comparison

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
**Current state**: MCP fails to Direct API fallback (binary).
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

#### I11: Natural Language Query Builder -- PARTIALLY IMPLEMENTED
**Current state**: Dashboard now supports NL queries that are routed to the agent chat for translation.
**What was done**: Query language toggle, autocomplete overlay, query helpers, and manual query bar added to Flutter dashboard panels (traces, logs, metrics, charts).
**Remaining**: The translation currently delegates to the agent; a dedicated NL-to-query microservice could reduce latency and token cost.

#### I12: Collaborative Investigations
**Current state**: Single-user sessions.
**Improvement**: Support multi-user investigation sessions:
- Share investigation link with team
- Real-time cursors showing who is looking at what
- Comments and annotations on findings
- Escalation workflow: SRE to Manager to Incident Commander

#### I13: Mobile-Responsive Dashboard
**Current state**: Flutter Web optimized for desktop.
**Improvement**: Add responsive breakpoints for tablet/mobile:
- Collapsible sidebar for panel navigation
- Swipeable panel cards on mobile
- Push notifications for critical alert findings

---

### 2.4 Intelligence & Learning Improvements

#### I14: Cross-Incident Knowledge Graph -- PARTIALLY IMPLEMENTED
**Current state**: `core/graph_service.py` implements a service dependency graph with blast radius analysis and causal inference. Memory bank stores investigation patterns.
**Remaining**: The knowledge graph is not yet persistent across sessions or queryable via natural language. Integration with Firestore for persistence is needed.

#### I15: Proactive Anomaly Detection -- PARTIALLY IMPLEMENTED
**Current state**: `tools/proactive/related_signals.py` provides `suggest_next_steps` for proactive signal analysis.
**Remaining**: Background monitoring mode (continuous polling, auto-investigation triggers) is not yet implemented.

#### I16: Investigation Quality Scoring -- IMPLEMENTED
**Current state**: `models/investigation.py` provides `calculate_score()` with weighted scoring across signal coverage, finding depth, root cause identification, remediation suggestions, and timeline completeness.
**Remaining**: Results are not yet surfaced in the Flutter UI as a post-investigation quality report.

#### I17: Fine-Tuned Prompt Optimization
**Current state**: Static system prompts with some dynamic composition via OPT-7 (dynamic root prompt).
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

| Priority | Item | Category | Complexity | Status |
|----------|------|----------|------------|--------|
| P0 | Fix all documentation discrepancies (D1-D12) | Docs | Low | **Mostly done** (D9-D12 remain) |
| P0 | Rate limiting middleware (I9) | Reliability | Medium | Open |
| P0 | CORS tightening (from audit follow-ups) | Security | Low | Open |
| P1 | Token budget forecasting (I7) | Reliability | Medium | Open |
| P1 | Investigation templates (I5) | UX/Intelligence | Medium | Open |
| P1 | Streaming panel results (I2) | Architecture | High | Open |
| P1 | Tool usage analytics (I4) | Operations | Medium | **Partially done** (tool error learning) |
| P2 | Circuit breaker dashboard (I6) | UX | Low | Open |
| P2 | NL query builder (I11) | UX | Medium | **Partially done** (dashboard NL queries) |
| P2 | Automated doc generation (I20) | DevOps | Medium | Open |

### Phase 5: Proactive SRE (Q2 2026)

**Theme**: The agent anticipates problems before users ask.

| Priority | Item | Category | Complexity | Status |
|----------|------|----------|------------|--------|
| P0 | Proactive anomaly detection (I15) | Intelligence | High | **Partially done** (suggest_next_steps) |
| P0 | Cross-incident knowledge graph (I14) | Intelligence | High | **Partially done** (graph_service.py) |
| P1 | Adaptive panel selection (I1) | Architecture | Medium | Open |
| P1 | Panel self-assessment & re-dispatch (I3) | Architecture | High | Open |
| P1 | Investigation quality scoring UI (I16) | Intelligence | Medium | **Backend done**, UI pending |
| P2 | Investigation history & replay (I10) | UX | Medium | Open |
| P2 | Graceful degradation hierarchy (I8) | Reliability | Medium | Open |
| P2 | Cost attribution (I19) | Operations | Medium | Open |

### Phase 6: Enterprise & Scale (Q3-Q4 2026)

**Theme**: Multi-team, multi-cloud, production-grade governance.

| Priority | Item | Category | Complexity | Status |
|----------|------|----------|------------|--------|
| P0 | Confirmation Bridge / HITL 2.0 (from PROJECT_PLAN Phase 4) | Safety | High | Open |
| P0 | Zero-Trust Identity propagation (from PROJECT_PLAN Phase 4) | Security | High | Open |
| P1 | Collaborative investigations (I12) | UX | High | Open |
| P1 | Canary deployment pipeline (I18) | DevOps | High | Open |
| P1 | Prompt A/B testing (I17) | Intelligence | Medium | Open |
| P2 | Mobile-responsive dashboard (I13) | UX | Medium | Open |
| P2 | Chaos Engineering Sub-Agent (from PROJECT_PLAN) | Intelligence | High | Open |
| P2 | Multi-cloud support (AWS CloudWatch, Azure Monitor) | Architecture | Very High | Open |

### Quick Wins (Can Be Done Immediately)

These items have low complexity and high impact:

1. ~~**Fix D1-D12 documentation discrepancies**~~ -- Mostly complete (D1-D8 fixed, D9-D12 open)
2. ~~**Add missing guides to docs/README.md index**~~ -- Done (D6, D7)
3. **Update README.md Mermaid diagram** -- Reflect Council architecture (D12 still open)
4. **Add CORS explicit allowlist** -- Security hardening
5. **Replace `time.sleep()` in tests with `freezegun`** -- Test quality
6. **Add `CONTRIBUTING.md`** -- Lower barrier for new contributors
7. **Create `CHANGELOG.md`** -- Separate release tracking from roadmap
8. **Add Spanner playbook code** -- `tools/playbooks/spanner.py` to match existing doc (D14)
9. **Document dashboard query language** -- New feature undocumented (D17)
10. **Update stale reference docs** -- `api.md`, `tools.md`, `security.md`, `testing.md` are 13+ days stale

---

## Part 4: Documentation Fix Recommendations

Below is the specific list of edits needed to bring all documentation into sync:

### Fix F1: `docs/PROJECT_PLAN.md` line 84
Change "Four parallel panels followed by synthesizer merge" to "Five parallel panels followed by synthesizer merge"
**Status**: Open (line 80 was fixed, line 84 was not)

### Fix F2: `CLAUDE.md` routers list -- DONE
Add "preferences" to the routers list.

### Fix F3: `CLAUDE.md` playbooks description -- DONE
Changed to "(GKE, Cloud Run, SQL, Pub/Sub, GCE, BigQuery)".

### Fix F4: `CLAUDE.md` sub_agents listing -- DONE
Added agent_debugger.py.

### Fix F5: `CLAUDE.md` test count -- DONE
Updated to "2277+ backend tests, 129 Flutter tests passing".

### Fix F6: `docs/README.md` Architecture section -- DONE
Added help_system.md, AGENTS_AND_TOOLS.md, system_instruction_snapshot_v1.md.

### Fix F7: `docs/README.md` Guides section -- DONE
Added dashboard_ui.md, frontend_testing.md, project_selector.md.

### Fix F8: `llm.txt` line 102 -- DONE
Updated to "~210+ files".

### Fix F9: `AGENTS.md` line 644
Clarify: "Target: 80% minimum gate on all code. 100% coverage target on new tools and core logic."
**Status**: Open

### Fix F10: `AGENTS.md` Core Components tree
Add council/, core/, memory/, models/, resources/ directories to the tree.
**Status**: Open

### Fix F11: `README.md` Mermaid diagram
Update to include Council of Experts architecture with 5 panels.
**Status**: Open

### Fix F12: Update all "Last verified" dates
Set all documents to 2026-02-15 after corrections are applied.
**Status**: Partially done -- several docs updated to 2026-02-15, some still stale.

### Fix F13 (New): `docs/PROJECT_PLAN.md` line 84
Same as F1 -- change "Four" to "Five" on line 84.

### Fix F14 (New): Add self_healing to CLAUDE.md playbooks list
Add "Self-Healing" to the playbooks description in CLAUDE.md.

### Fix F15 (New): Create dashboard query language documentation
Add a guide in `docs/guides/` describing the query language features, autocomplete, NL support.

### Fix F16 (New): Update stale reference docs
Update `docs/reference/api.md`, `tools.md`, `security.md` and `docs/testing/testing.md` to reflect current codebase (196 test files, new tools, new API endpoints).

---

*Generated: 2026-02-11, Updated: 2026-02-15 -- Documentation Review & Roadmap*
