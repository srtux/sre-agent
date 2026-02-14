# Online Research & Self-Healing Agent Architecture

> **Status**: Online Research tools — **Implemented** (Phase 3.7).
> Self-Healing Loop — **Proposed Architecture** (Phase 4+).

This document covers two interconnected capabilities:

1. **Online Research** — Allowing the agent to search Google and fetch web content.
2. **Self-Healing Agent Loop** — A closed-loop architecture where the agent observes its own behavior, diagnoses issues in its own source code, and submits PRs to fix itself.

---

## Part 1: Online Research Tools

### Overview

The agent can search Google and fetch web pages to augment its knowledge during investigations. This is useful when the agent encounters unfamiliar errors, needs up-to-date documentation, or wants to verify query syntax.

### Tools

| Tool | Purpose | Memory Integration |
|------|---------|-------------------|
| `search_google` | Search Google Custom Search JSON API | Auto-saves result summary to memory |
| `fetch_web_page` | Fetch a URL and extract readable text | Auto-saves content preview to memory |

### `search_google`

Searches Google via the [Custom Search JSON API](https://developers.google.com/custom-search/v1/overview).

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | required | The search query |
| `num_results` | `int` | 5 | Number of results (clamped to 1-10) |
| `site_restrict` | `str \| None` | `None` | Limit to a specific domain (e.g., `cloud.google.com`) |

**Returns** (`BaseToolResponse`):
```json
{
  "status": "success",
  "result": {
    "query": "cloud logging filter syntax",
    "total_results": "42000",
    "search_time_seconds": 0.23,
    "results": [
      {
        "title": "Cloud Logging query language",
        "link": "https://cloud.google.com/logging/docs/view/logging-query-language",
        "snippet": "Use the Logging query language to query...",
        "display_link": "cloud.google.com"
      }
    ]
  }
}
```

**When to use:**
- Looking up query syntax for Cloud Logging, PromQL, BigQuery SQL.
- Researching unfamiliar error messages or status codes.
- Finding GCP best practices or configuration references.
- Accessing documentation that may have changed since training data.

### `fetch_web_page`

Fetches a URL and extracts readable text content. HTML is automatically stripped using Python's stdlib `HTMLParser` — no external dependencies.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Full HTTP(S) URL to fetch |
| `max_chars` | `int` | 15000 | Max content chars (clamped to 1000-50000) |

**Returns** (`BaseToolResponse`):
```json
{
  "status": "success",
  "result": {
    "url": "https://cloud.google.com/logging/docs/...",
    "title": "Cloud Logging query language",
    "content": "Extracted text content...",
    "content_type": "text/html; charset=utf-8",
    "truncated": false,
    "char_count": 8432
  }
}
```

**When to use:**
- Reading documentation pages found via `search_google`.
- Extracting detailed error descriptions from knowledge base articles.
- Getting configuration examples or API reference details.
- Reading Stack Overflow answers, blog posts, or release notes.

### Configuration

Both tools require a [Google Programmable Search Engine](https://programmablesearchengine.google.com/):

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CUSTOM_SEARCH_API_KEY` | API key from Google Cloud Console (APIs & Services > Credentials) | Yes |
| `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` | Programmable Search Engine ID (cx) | Yes |

**Setup steps:**
1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/) and create a search engine.
2. Set it to "Search the entire web" for general research capability.
3. Go to GCP Console > APIs & Services > Enable "Custom Search API".
4. Create an API key and set both environment variables.

### Memory Integration

Both tools automatically persist results to the agent's memory:
- `search_google` saves: query + top 3 result titles.
- `fetch_web_page` saves: page title + first 200 chars of content.

This means future investigations can recall past research via `search_memory`:
```
Agent: "Let me check if I've researched PromQL syntax before..."
→ search_memory(query="PromQL syntax") → Found: "Web search for 'PromQL rate syntax': ..."
```

Memory save failures are silently logged — they never block the primary tool result.

### Registration

The tools are registered at all standard integration points:

| Location | Registration |
|----------|-------------|
| `tools/__init__.py` | Lazy imports: `search_google`, `fetch_web_page` |
| `tools/config.py` | `ToolCategory.RESEARCH` category, 2 `ToolConfig` entries |
| `agent.py` | `base_tools`, `slim_tools`, `TOOL_NAME_MAP` |
| `council/tool_registry.py` | `SHARED_RESEARCH_TOOLS` (included in `ROOT_CAUSE_ANALYST_TOOLS`, `ORCHESTRATOR_TOOLS`) |
| `tools/common/decorators.py` | Circuit breaker protection |

### Testing

28 unit tests in `tests/unit/sre_agent/tools/test_research.py`:
- HTML extraction: tag stripping, script/style/nav skipping, malformed HTML, title extraction
- `search_google`: success, timeout, HTTP errors, missing config, param clamping, empty results, memory failure resilience
- `fetch_web_page`: success (HTML/JSON/plain text), truncation, redirects, invalid URLs, memory failure resilience

---

## Part 2: Self-Healing Agent Architecture

### Vision

The Auto SRE agent should be able to **observe its own behavior, diagnose issues in its own code, and submit pull requests to fix itself**. Combined with an existing CI/CD pipeline that auto-deploys on merge, this creates a fully autonomous self-improvement loop.

### The OODA Self-Healing Loop

This architecture follows the [OODA loop](docs/concepts/autonomous_reliability.md) already established in the project, applied to the agent itself:

```
┌─────────────────────────────────────────────────────────────┐
│                    SELF-HEALING LOOP                         │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────┐ │
│  │ OBSERVE  │───>│  ORIENT  │───>│  DECIDE  │───>│  ACT  │ │
│  └──────────┘    └──────────┘    └──────────┘    └───────┘ │
│       │                                              │      │
│       │          CI/CD Auto-Deploy                    │      │
│       └──────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| Phase | What Happens | Tools Used |
|-------|-------------|------------|
| **OBSERVE** | Analyze own traces, logs, metrics. Detect anti-patterns, failures, regressions. | `analyze_and_learn_from_traces`, `detect_agent_anti_patterns`, `list_agent_traces`, `mcp_execute_sql` |
| **ORIENT** | Correlate failures with source code. Identify which file/function is responsible. | `search_google`, `fetch_web_page`, `github_read_file` (proposed), `github_search_code` (proposed) |
| **DECIDE** | Generate a fix strategy. Draft code changes. Determine if human review is needed. | `search_memory`, `get_recommended_investigation_strategy`, LLM reasoning |
| **ACT** | Create a branch, commit changes, open a PR. CI/CD pipeline validates and deploys. | `github_create_pr` (proposed), `github_commit_file` (proposed) |

### What Already Exists (Foundations)

The project already has strong foundations for each OODA phase:

#### OBSERVE — Agent Self-Analysis (Implemented)

| Capability | Tool/Module | Status |
|-----------|-------------|--------|
| List past agent traces | `list_agent_traces` | Implemented |
| Reconstruct agent interaction tree | `reconstruct_agent_interaction` | Implemented |
| Detect anti-patterns (retries, token waste, long chains) | `detect_agent_anti_patterns` | Implemented |
| Analyze token usage breakdown | `analyze_agent_token_usage` | Implemented |
| Automatic failure learning | `after_tool_memory_callback` | Implemented |
| Automatic success recording | `after_tool_memory_callback` | Implemented |
| Tool error pattern sharing | `record_tool_failure_pattern` | Implemented |
| Agent debugger sub-agent | `agent_debugger` | Implemented |

#### ORIENT — Knowledge Augmentation (Partially Implemented)

| Capability | Tool/Module | Status |
|-----------|-------------|--------|
| Search Google for context | `search_google` | **Implemented** |
| Fetch documentation pages | `fetch_web_page` | **Implemented** |
| Read own source code from GitHub | — | **Proposed** |
| Search code for patterns | — | **Proposed** |
| Correlate failures with code changes | `correlate_changes_with_incident` | Implemented (GCP Audit Logs) |

#### DECIDE — Strategy (Implemented)

| Capability | Tool/Module | Status |
|-----------|-------------|--------|
| Recall past investigation patterns | `get_recommended_investigation_strategy` | Implemented |
| Search memory for similar issues | `search_memory` | Implemented |
| Pattern reinforcement learning | `complete_investigation` | Implemented |
| Human approval workflow | `core/approval.py` | Implemented |

#### ACT — GitHub Integration (Proposed)

| Capability | Tool/Module | Status |
|-----------|-------------|--------|
| Read files from GitHub | `github_read_file` | **Proposed** |
| Search code in repository | `github_search_code` | **Proposed** |
| Create branches | `github_create_branch` | **Proposed** |
| Create/update files | `github_commit_file` | **Proposed** |
| Open pull requests | `github_create_pr` | **Proposed** |
| CI/CD auto-deploy on merge | Cloud Build pipeline | **Exists** |

### Proposed GitHub Tool Set

A new `sre_agent/tools/github/` module with tools for interacting with the agent's own repository.

#### Tool: `github_read_file`

Read a file from the agent's own GitHub repository.

```python
@adk_tool
async def github_read_file(
    file_path: str,
    ref: str = "main",
    repo: str = "srtux/sre-agent",
) -> BaseToolResponse:
    """Read a file from the agent's GitHub repository."""
```

**Use cases:**
- Reading own source code to understand a tool's implementation.
- Checking current prompt configuration.
- Reviewing test files for a module under investigation.

#### Tool: `github_search_code`

Search the agent's codebase for patterns.

```python
@adk_tool
async def github_search_code(
    query: str,
    file_extension: str | None = None,
    repo: str = "srtux/sre-agent",
) -> BaseToolResponse:
    """Search the agent's codebase for code patterns."""
```

**Use cases:**
- Finding where a specific tool is defined.
- Locating configuration for a feature flag.
- Searching for similar patterns to guide a fix.

#### Tool: `github_create_pr`

Create a pull request with proposed changes.

```python
@adk_tool
async def github_create_pr(
    title: str,
    body: str,
    branch_name: str,
    file_changes: list[dict],  # [{path, content, message}]
    base: str = "main",
    repo: str = "srtux/sre-agent",
    draft: bool = True,
    labels: list[str] = ["auto-fix", "agent-generated"],
) -> BaseToolResponse:
    """Create a pull request with the agent's proposed changes."""
```

**Use cases:**
- Submitting a fix for a detected anti-pattern.
- Proposing a prompt improvement based on trace analysis.
- Adding a new playbook based on a resolved investigation.

**Safety considerations:**
- PRs are created as **drafts** by default — requiring human review.
- PRs are labeled `agent-generated` for easy filtering.
- The `core/approval.py` human approval workflow gates destructive actions.
- The existing `ai-code-review.yml` GitHub Action reviews all PRs with AI.

#### Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | Personal access token or GitHub App token with `repo` scope | Yes |
| `GITHUB_REPO` | Repository in `owner/name` format (default: `srtux/sre-agent`) | No |

### Self-Healing Pipeline: End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. SCHEDULED SELF-ANALYSIS (Cloud Scheduler or user-triggered) │
│     │                                                           │
│     ▼                                                           │
│  2. analyze_and_learn_from_traces(hours_back=24)                │
│     → mcp_execute_sql(sql) → List of recent agent traces        │
│     │                                                           │
│     ▼                                                           │
│  3. detect_agent_anti_patterns(trace_id)                        │
│     → Finds: excessive retries on list_log_entries              │
│     → Finds: token waste in root_cause_analyst                  │
│     │                                                           │
│     ▼                                                           │
│  4. search_google("list_log_entries filter best practices")     │
│     → fetch_web_page(result_url)                                │
│     → Learns correct filter syntax from docs                    │
│     │                                                           │
│     ▼                                                           │
│  5. github_read_file("sre_agent/tools/clients/logging.py")     │
│     → Reads the current implementation                          │
│     → Identifies: missing input validation causes retries       │
│     │                                                           │
│     ▼                                                           │
│  6. github_create_pr(                                           │
│       title="fix: add input validation to list_log_entries",    │
│       file_changes=[{path: "sre_agent/tools/clients/logging.py",│
│                      content: "...improved code..."}],          │
│       draft=True,                                               │
│       labels=["auto-fix", "agent-generated"]                    │
│     )                                                           │
│     │                                                           │
│     ▼                                                           │
│  7. CI/CD PIPELINE (Cloud Build)                                │
│     → ai-code-review.yml reviews the PR                         │
│     → Tests run automatically                                   │
│     → Human approves merge                                      │
│     │                                                           │
│     ▼                                                           │
│  8. AUTO-DEPLOY                                                 │
│     → cloudbuild.yaml deploys new version                       │
│     → Agent restarts with fix applied                           │
│     │                                                           │
│     ▼                                                           │
│  9. VERIFICATION (next analysis cycle)                          │
│     → analyze_and_learn_from_traces confirms fix worked         │
│     → complete_investigation records the pattern                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Safety Guardrails

Self-modification requires strong safety measures:

| Guardrail | Mechanism | Status |
|-----------|-----------|--------|
| **Draft PRs** | All agent-generated PRs are drafts by default | Proposed |
| **Human approval** | PRs require human merge approval | Exists (GitHub) |
| **AI code review** | `ai-code-review.yml` reviews all PRs | Exists |
| **CI/CD gating** | Tests + evals must pass before deploy | Exists (Cloud Build) |
| **Policy engine** | `core/policy_engine.py` gates destructive actions | Exists |
| **Human-in-the-loop** | `core/approval.py` workflow for risky actions | Exists |
| **Labeled PRs** | `agent-generated` label for audit trail | Proposed |
| **Branch protection** | `main` branch requires PR reviews | Standard |
| **Rollback** | Cloud Run revision rollback if deploy fails | Exists |
| **Token budget** | `SRE_AGENT_TOKEN_BUDGET` limits per-request cost | Exists |

### Metrics for Self-Healing Effectiveness

The agent should track its own improvement:

| Metric | Source | Target |
|--------|--------|--------|
| Anti-patterns per 24h | `detect_agent_anti_patterns` | Decreasing trend |
| Tool retry rate | `after_tool_memory_callback` | < 5% |
| Mean investigation time | Agent traces (duration_ms) | Decreasing trend |
| Token efficiency (output/input ratio) | `analyze_agent_token_usage` | < 3:1 |
| Investigation success rate | `complete_investigation` calls | Increasing |
| PRs auto-generated | GitHub API | Tracking |
| PRs merged successfully | GitHub API | > 80% acceptance |

### Implementation Roadmap

| Phase | Scope | Prerequisites |
|-------|-------|---------------|
| **Phase 4.1** | GitHub read tools (`github_read_file`, `github_search_code`) | `GITHUB_TOKEN` env var |
| **Phase 4.2** | GitHub write tools (`github_create_branch`, `github_commit_file`, `github_create_pr`) | Phase 4.1 + branch protection |
| **Phase 4.3** | Scheduled self-analysis playbook (automated OODA cycle) | Phase 4.2 + Cloud Scheduler |
| **Phase 4.4** | Self-healing verification loop (confirm fixes worked) | Phase 4.3 + metrics dashboard |
| **Phase 4.5** | Autonomous prompt tuning (optimize own system instructions) | Phase 4.4 + A/B eval framework |

### Architectural Principles

1. **Human-in-the-loop by default** — The agent proposes, humans approve. Draft PRs ensure no unreviewed code reaches production.
2. **Progressive autonomy** — Start with read-only GitHub access, then draft PRs, then (eventually) auto-merge for low-risk changes like documentation or typo fixes.
3. **Audit trail** — Every self-modification is traceable: agent trace → anti-pattern → PR → deploy → verification.
4. **Fail-safe** — If CI/CD fails, the old version keeps running. Cloud Run maintains previous revisions.
5. **Memory-driven** — The agent remembers what worked and what didn't. Failed fix attempts are recorded to avoid repeating them.

---

## Related Documentation

- [Memory Best Practices](memory.md) — How the learning system works
- [Agent Orchestration](agent_orchestration.md) — Council of Experts architecture
- [Autonomous Reliability](autonomous_reliability.md) — OODA loop design philosophy
- [Configuration Reference](../reference/configuration.md) — Environment variables
- [Tools Reference](../reference/tools.md) — Full tool catalog
- [CI/CD Pipeline](../../.github/CICD.md) — Deployment pipeline

---

*Last verified: 2026-02-14 — Auto SRE Team*
