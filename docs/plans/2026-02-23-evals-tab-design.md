# Evals Tab Design — AgentOps UI

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an Evals tab to the AgentOps UI that lets users configure GenAI evaluation for agents and monitor evaluation scores from macro (agent list with summary scores) to micro (per-agent metrics chart + span-level scores).

**Architecture:** Two-level drill-down within a new top-level tab. A shared setup wizard modal (usable from both the Evals tab and the Agent Registry page) handles eval configuration. Data flows through React Query hooks calling the existing `/api/v1/evals/` backend endpoints.

**Tech Stack:** React, TypeScript, TanStack React Query, ECharts (via EChartWrapper), existing AgentOps patterns (AgentContext, DashboardFilterContext).

---

## Components

### 1. EvalsPage (`components/evals/EvalsPage.tsx`)

Top-level component rendered when `activeTab === 'evals'`.

**Two views based on state:**

- **Agent List View** (default, no `selectedAgent`):
  - Header: "AI Evaluations" title + "Configure Agent" button (opens wizard)
  - Empty state: centered prompt with CTA when no eval configs exist
  - Cards grid: one card per configured agent showing:
    - Agent name + enabled/disabled badge
    - Average scores per metric (last 24h)
    - Sampling rate
    - Actions: View Details, Edit Config, Delete

- **Agent Detail View** (`selectedAgent` is set):
  - Back button → returns to list view
  - Agent header with config summary (enabled, sampling rate, metrics)
  - EvalMetricsPanel (reuse existing line chart, filtered to this agent)
  - Recent span-level eval scores table

**URL persistence:** `?tab=evals&agent=<name>` — the `agent` param selects the detail view.

### 2. EvalAgentCard (`components/evals/EvalAgentCard.tsx`)

Summary card for one agent in the list view.

- Displays: agent name, enabled badge, metric scores (color-coded), sampling rate, last eval timestamp
- Click → navigates to detail view
- Edit button → opens wizard in edit mode
- Delete button → confirmation then DELETE endpoint

### 3. EvalSetupWizard (`components/evals/EvalSetupWizard.tsx`)

Modal dialog for configuring eval on an agent. Shared between Evals tab and Registry page.

**Step 1 — Configure:**
- Agent selector (dropdown of available agents from AgentContext, pre-filled when opened from Registry)
- Metric toggles: coherence, groundedness, fluency, safety (all on by default)
- Sampling rate slider: 0.0–1.0 (default 1.0)

**Step 2 — Confirm & Save:**
- Review summary
- Save button → POST `/api/v1/evals/config/{agent_name}`
- On success: close modal, invalidate `useEvalConfigs` cache, navigate to Evals tab if opened from Registry

### 4. EvalDetailView (`components/evals/EvalDetailView.tsx`)

Detail view for a single agent's eval metrics.

- Config summary bar (metrics enabled, sampling rate, edit/delete actions)
- EvalMetricsPanel (existing component, passed `serviceName` prop for this agent)
- Time range selector (reuse DashboardFilterContext `timeRange`)

### 5. Registry Integration

Add an "Evals" action button to each agent card in `RegistryPage.tsx`:
- If agent has eval config → navigate to `?tab=evals&agent=<name>`
- If not → open `EvalSetupWizard` modal with agent pre-selected

---

## Data Layer

### Hooks

**`useEvalConfigs()` (new)**
- Fetches: `GET /api/v1/evals/config`
- Returns: `EvalConfig[]`
- staleTime: 30s
- Used by: EvalsPage list, Registry "Evals" button logic

**`useEvalMetrics(hours, serviceName)` (existing)**
- Fetches: `GET /api/v1/evals/metrics/aggregate`
- Returns: `EvalMetricPoint[]`
- Used by: EvalDetailView chart

**`useUpsertEvalConfig()` (new mutation)**
- Calls: `POST /api/v1/evals/config/{agent_name}`
- On success: invalidates `useEvalConfigs` query key
- Used by: EvalSetupWizard

**`useDeleteEvalConfig()` (new mutation)**
- Calls: `DELETE /api/v1/evals/config/{agent_name}`
- On success: invalidates `useEvalConfigs` query key
- Used by: EvalAgentCard delete action

### TypeScript Interfaces

```typescript
interface EvalConfig {
  agent_name: string;
  is_enabled: boolean;
  sampling_rate: number;       // 0.0–1.0
  metrics: string[];           // e.g., ['coherence', 'groundedness']
  last_eval_timestamp: string | null;
}

interface EvalConfigsResponse {
  configs: EvalConfig[];
}
```

---

## Guest/Demo Mode

Backend already returns synthetic data for guest mode:
- `GET /evals/config` → `{ configs: [] }` (empty)
- `GET /evals/metrics/aggregate` → synthetic metrics
- `POST /evals/config/{agent}` → echoes back without persisting

For the Evals tab empty state in guest mode, show a demo banner explaining this is sample data, and pre-populate with synthetic eval configs client-side so the UI is explorable.

---

## Navigation Flow

```
Evals Tab (no configs)    → Empty State → "Configure Agent" → Wizard Modal → Save → List View
Evals Tab (has configs)   → Agent List → Click Agent → Agent Detail View → Back → Agent List
Evals Tab                 → "Configure Agent" button → Wizard Modal → Save → List refreshes
Registry Page             → Agent Card "Evals" button → Wizard Modal (if unconfigured) or Evals Tab Detail
```

---

## Metrics

Fixed set of 4 GenAI evaluation metrics:
- **coherence** — response logical consistency
- **groundedness** — factual accuracy against sources
- **fluency** — language quality
- **safety** — harmful content detection

All enabled by default in the wizard. Users toggle individual metrics on/off.
