# Evals Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an Evals tab to the AgentOps UI with a setup wizard modal, agent list with summary scores, and per-agent detail drill-down — plus an "Evals" action button on the Agent Registry page.

**Architecture:** New `evals` tab value in the existing tab-based navigation. Shared `EvalSetupWizard` modal reusable from both Evals tab and Registry page. Two React Query hooks for config CRUD and a refactored `useEvalMetrics` that accepts an explicit `serviceName`. All components follow the existing dark-theme styling patterns (`#1E293B` backgrounds, `#334155` borders, cyan accents).

**Tech Stack:** React 18, TypeScript, TanStack React Query (mutations + queries), ECharts (via existing EChartWrapper), axios, lucide-react icons.

---

### Task 1: TypeScript interfaces for EvalConfig

**Files:**
- Modify: `agent_ops_ui/src/types.ts`

**Step 1: Add EvalConfig and EvalConfigsResponse interfaces**

After the existing `EvalMetricsAggregateResponse` interface (around line 283), add:

```typescript
export interface EvalConfig {
  agent_name: string
  is_enabled: boolean
  sampling_rate: number
  metrics: string[]
  last_eval_timestamp: string | null
}

export interface EvalConfigsResponse {
  configs: EvalConfig[]
}
```

Also add `'evals'` to the `Tab` type union. The current definition at line 80 is:

```typescript
export type Tab = 'agents' | 'tools' | 'dashboard' | 'traces' | 'logs' | 'topology' | 'trajectory';
```

Change to:

```typescript
export type Tab = 'agents' | 'tools' | 'dashboard' | 'traces' | 'logs' | 'topology' | 'trajectory' | 'evals';
```

**Step 2: Verify TypeScript compiles**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add agent_ops_ui/src/types.ts
git commit -m "feat(evals-tab): add EvalConfig types and evals tab type"
```

---

### Task 2: useEvalConfigs hook + mutation hooks

**Files:**
- Create: `agent_ops_ui/src/hooks/useEvalConfigs.ts`

**Step 1: Create the hook file**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import type { EvalConfig, EvalConfigsResponse } from '../types'

const EVAL_CONFIGS_KEY = ['eval-configs'] as const

async function fetchEvalConfigs(): Promise<EvalConfig[]> {
  const res = await axios.get<EvalConfigsResponse>('/api/v1/evals/config')
  return res.data.configs
}

export function useEvalConfigs() {
  return useQuery({
    queryKey: EVAL_CONFIGS_KEY,
    queryFn: fetchEvalConfigs,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}

interface UpsertEvalConfigParams {
  agentName: string
  isEnabled: boolean
  samplingRate: number
  metrics: string[]
}

export function useUpsertEvalConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: UpsertEvalConfigParams) => {
      const res = await axios.post(`/api/v1/evals/config/${encodeURIComponent(params.agentName)}`, {
        is_enabled: params.isEnabled,
        sampling_rate: params.samplingRate,
        metrics: params.metrics,
      })
      return res.data.config as EvalConfig
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EVAL_CONFIGS_KEY })
    },
  })
}

export function useDeleteEvalConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (agentName: string) => {
      await axios.delete(`/api/v1/evals/config/${encodeURIComponent(agentName)}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EVAL_CONFIGS_KEY })
    },
  })
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add agent_ops_ui/src/hooks/useEvalConfigs.ts
git commit -m "feat(evals-tab): add useEvalConfigs, useUpsertEvalConfig, useDeleteEvalConfig hooks"
```

---

### Task 3: Refactor useEvalMetrics to accept explicit serviceName

The existing `useEvalMetrics` hook reads `serviceName` from `useDashboardFilters().selectedAgents`. The Evals detail view needs to pass an explicit agent name without depending on the dashboard filter context.

**Files:**
- Modify: `agent_ops_ui/src/hooks/useEvalMetrics.ts`
- Modify: `agent_ops_ui/src/components/dashboard/panels/EvalMetricsPanel.tsx`

**Step 1: Add optional `serviceName` parameter to useEvalMetrics**

Change the hook signature from:

```typescript
export function useEvalMetrics(hours: number) {
  const { selectedAgents } = useDashboardFilters()
  const { projectId } = useAgentContext()
  const serviceName = selectedAgents.length > 0 ? selectedAgents[0] : ''
```

To:

```typescript
export function useEvalMetrics(hours: number, explicitServiceName?: string) {
  const { selectedAgents } = useDashboardFilters()
  const { projectId } = useAgentContext()
  const serviceName = explicitServiceName ?? (selectedAgents.length > 0 ? selectedAgents[0] : '')
```

Update the query key to include the resolved serviceName (it already does — `['eval-metrics', projectId, serviceName, hours]` — so no change needed there).

**Step 2: Verify existing EvalMetricsPanel still works**

`EvalMetricsPanel` calls `useEvalMetrics(hours)` without the second arg, so it defaults to the filter context behavior. No changes needed.

**Step 3: Verify TypeScript compiles**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 4: Commit**

```bash
git add agent_ops_ui/src/hooks/useEvalMetrics.ts
git commit -m "feat(evals-tab): allow useEvalMetrics to accept explicit serviceName"
```

---

### Task 4: EvalSetupWizard modal component

**Files:**
- Create: `agent_ops_ui/src/components/evals/EvalSetupWizard.tsx`

**Step 1: Create the wizard modal**

```typescript
import React, { useState, useCallback } from 'react'
import { useAgentContext } from '../../contexts/AgentContext'
import { useUpsertEvalConfig } from '../../hooks/useEvalConfigs'
import type { EvalConfig } from '../../types'
import { X, Check, ChevronRight } from 'lucide-react'

const AVAILABLE_METRICS = ['coherence', 'groundedness', 'fluency', 'safety'] as const

interface EvalSetupWizardProps {
  isOpen: boolean
  onClose: () => void
  /** Pre-fill agent name (e.g., from Registry page). */
  initialAgentName?: string
  /** Existing config to edit. If provided, pre-fills all fields. */
  existingConfig?: EvalConfig
  /** Called after successful save with the agent name. */
  onSaved?: (agentName: string) => void
}

export default function EvalSetupWizard({
  isOpen,
  onClose,
  initialAgentName,
  existingConfig,
  onSaved,
}: EvalSetupWizardProps) {
  const { availableAgents } = useAgentContext()
  const upsertMutation = useUpsertEvalConfig()

  const [step, setStep] = useState<1 | 2>(1)
  const [agentName, setAgentName] = useState(existingConfig?.agent_name ?? initialAgentName ?? '')
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(
    existingConfig?.metrics ?? [...AVAILABLE_METRICS],
  )
  const [samplingRate, setSamplingRate] = useState(existingConfig?.sampling_rate ?? 1.0)
  const [error, setError] = useState<string | null>(null)

  const toggleMetric = useCallback((metric: string) => {
    setSelectedMetrics(prev =>
      prev.includes(metric) ? prev.filter(m => m !== metric) : [...prev, metric],
    )
  }, [])

  const handleSave = useCallback(async () => {
    if (!agentName.trim()) {
      setError('Please select an agent.')
      return
    }
    if (selectedMetrics.length === 0) {
      setError('Please select at least one metric.')
      return
    }
    setError(null)
    try {
      await upsertMutation.mutateAsync({
        agentName: agentName.trim(),
        isEnabled: true,
        samplingRate,
        metrics: selectedMetrics,
      })
      onSaved?.(agentName.trim())
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration.')
    }
  }, [agentName, selectedMetrics, samplingRate, upsertMutation, onSaved, onClose])

  if (!isOpen) return null

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <span style={styles.title}>
            {existingConfig ? 'Edit Evaluation Config' : 'Set Up AI Evaluation'}
          </span>
          <button style={styles.closeBtn} onClick={onClose}><X size={18} /></button>
        </div>

        {/* Step indicator */}
        <div style={styles.stepIndicator}>
          <span style={step >= 1 ? styles.stepActive : styles.stepInactive}>1. Configure</span>
          <ChevronRight size={14} style={{ color: '#64748B' }} />
          <span style={step >= 2 ? styles.stepActive : styles.stepInactive}>2. Confirm</span>
        </div>

        {step === 1 && (
          <div style={styles.body}>
            {/* Agent selector */}
            <label style={styles.label}>Agent</label>
            <select
              style={styles.select}
              value={agentName}
              onChange={e => setAgentName(e.target.value)}
              disabled={!!existingConfig}
            >
              <option value="">Select an agent…</option>
              {availableAgents.map(a => (
                <option key={a.serviceName} value={a.serviceName}>
                  {a.displayName || a.serviceName}
                </option>
              ))}
            </select>

            {/* Metric toggles */}
            <label style={{ ...styles.label, marginTop: '16px' }}>Metrics</label>
            <div style={styles.metricsGrid}>
              {AVAILABLE_METRICS.map(metric => (
                <button
                  key={metric}
                  style={selectedMetrics.includes(metric) ? styles.metricOn : styles.metricOff}
                  onClick={() => toggleMetric(metric)}
                >
                  {selectedMetrics.includes(metric) && <Check size={14} />}
                  {metric.charAt(0).toUpperCase() + metric.slice(1)}
                </button>
              ))}
            </div>

            {/* Sampling rate */}
            <label style={{ ...styles.label, marginTop: '16px' }}>
              Sampling Rate: {Math.round(samplingRate * 100)}%
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={samplingRate}
              onChange={e => setSamplingRate(parseFloat(e.target.value))}
              style={styles.slider}
            />

            <button style={styles.nextBtn} onClick={() => setStep(2)} disabled={!agentName}>
              Next <ChevronRight size={14} />
            </button>
          </div>
        )}

        {step === 2 && (
          <div style={styles.body}>
            <div style={styles.summaryCard}>
              <div style={styles.summaryRow}><span style={styles.summaryLabel}>Agent</span><span>{agentName}</span></div>
              <div style={styles.summaryRow}><span style={styles.summaryLabel}>Metrics</span><span>{selectedMetrics.join(', ')}</span></div>
              <div style={styles.summaryRow}><span style={styles.summaryLabel}>Sampling</span><span>{Math.round(samplingRate * 100)}%</span></div>
            </div>

            {error && <div style={styles.error}>{error}</div>}

            <div style={styles.btnRow}>
              <button style={styles.backBtn} onClick={() => setStep(1)}>Back</button>
              <button
                style={styles.saveBtn}
                onClick={handleSave}
                disabled={upsertMutation.isPending}
              >
                {upsertMutation.isPending ? 'Saving…' : 'Save & Enable'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex',
    alignItems: 'center', justifyContent: 'center', zIndex: 1000,
  },
  modal: {
    background: '#1E293B', border: '1px solid #334155', borderRadius: '12px',
    width: '480px', maxHeight: '90vh', overflow: 'auto',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '16px 20px', borderBottom: '1px solid #334155',
  },
  title: { fontSize: '16px', fontWeight: 600, color: '#E2E8F0' },
  closeBtn: {
    background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', padding: '4px',
  },
  stepIndicator: {
    display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 20px',
    borderBottom: '1px solid #334155', fontSize: '13px',
  },
  stepActive: { color: '#06B6D4', fontWeight: 600 },
  stepInactive: { color: '#64748B' },
  body: { padding: '20px' },
  label: { display: 'block', fontSize: '13px', fontWeight: 600, color: '#94A3B8', marginBottom: '8px' },
  select: {
    width: '100%', padding: '8px 12px', background: '#0F172A', border: '1px solid #334155',
    borderRadius: '6px', color: '#E2E8F0', fontSize: '14px', outline: 'none',
  },
  metricsGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' },
  metricOn: {
    display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 12px',
    background: 'rgba(6,182,212,0.15)', border: '1px solid #06B6D4', borderRadius: '6px',
    color: '#06B6D4', fontSize: '13px', fontWeight: 500, cursor: 'pointer',
  },
  metricOff: {
    display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 12px',
    background: '#0F172A', border: '1px solid #334155', borderRadius: '6px',
    color: '#94A3B8', fontSize: '13px', cursor: 'pointer',
  },
  slider: { width: '100%', accentColor: '#06B6D4' },
  nextBtn: {
    marginTop: '20px', width: '100%', padding: '10px', background: '#06B6D4', border: 'none',
    borderRadius: '6px', color: '#0F172A', fontWeight: 600, fontSize: '14px',
    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px',
  },
  summaryCard: {
    background: '#0F172A', border: '1px solid #334155', borderRadius: '8px', padding: '16px',
    display: 'flex', flexDirection: 'column', gap: '12px',
  },
  summaryRow: { display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: '#E2E8F0' },
  summaryLabel: { color: '#94A3B8', fontWeight: 500 },
  error: {
    marginTop: '12px', padding: '8px 12px', background: 'rgba(239,68,68,0.15)',
    border: '1px solid #EF4444', borderRadius: '6px', color: '#EF4444', fontSize: '13px',
  },
  btnRow: { display: 'flex', gap: '12px', marginTop: '20px' },
  backBtn: {
    flex: 1, padding: '10px', background: 'transparent', border: '1px solid #334155',
    borderRadius: '6px', color: '#94A3B8', fontWeight: 500, cursor: 'pointer',
  },
  saveBtn: {
    flex: 2, padding: '10px', background: '#06B6D4', border: 'none',
    borderRadius: '6px', color: '#0F172A', fontWeight: 600, cursor: 'pointer',
  },
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add agent_ops_ui/src/components/evals/EvalSetupWizard.tsx
git commit -m "feat(evals-tab): add EvalSetupWizard modal component"
```

---

### Task 5: EvalAgentCard component

**Files:**
- Create: `agent_ops_ui/src/components/evals/EvalAgentCard.tsx`

**Step 1: Create the card component**

```typescript
import React from 'react'
import type { EvalConfig } from '../../types'
import { Settings, Trash2 } from 'lucide-react'

const METRIC_COLORS: Record<string, string> = {
  coherence: '#06B6D4',
  groundedness: '#8B5CF6',
  fluency: '#10B981',
  safety: '#F59E0B',
}

interface EvalAgentCardProps {
  config: EvalConfig
  onSelect: (agentName: string) => void
  onEdit: (config: EvalConfig) => void
  onDelete: (agentName: string) => void
}

export default function EvalAgentCard({ config, onSelect, onEdit, onDelete }: EvalAgentCardProps) {
  return (
    <div style={styles.card} onClick={() => onSelect(config.agent_name)}>
      {/* Header */}
      <div style={styles.cardHeader}>
        <div style={styles.agentName}>{config.agent_name}</div>
        <span style={config.is_enabled ? styles.badgeOn : styles.badgeOff}>
          {config.is_enabled ? 'Enabled' : 'Disabled'}
        </span>
      </div>

      {/* Metrics scores (placeholder until aggregate data is fetched) */}
      <div style={styles.metricsRow}>
        {config.metrics.map(metric => (
          <div key={metric} style={styles.metricChip}>
            <span style={{
              display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%',
              background: METRIC_COLORS[metric] ?? '#94A3B8',
            }} />
            <span style={styles.metricLabel}>
              {metric.charAt(0).toUpperCase() + metric.slice(1)}
            </span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <span style={styles.samplingText}>
          Sampling: {Math.round(config.sampling_rate * 100)}%
        </span>
        <div style={styles.actions} onClick={e => e.stopPropagation()}>
          <button style={styles.actionBtn} onClick={() => onEdit(config)} title="Edit config">
            <Settings size={14} />
          </button>
          <button
            style={{ ...styles.actionBtn, color: '#EF4444' }}
            onClick={() => onDelete(config.agent_name)}
            title="Delete config"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#1E293B', border: '1px solid #334155', borderRadius: '8px', padding: '16px',
    cursor: 'pointer', transition: 'border-color 0.15s',
  },
  cardHeader: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px',
  },
  agentName: { fontSize: '15px', fontWeight: 600, color: '#E2E8F0' },
  badgeOn: {
    fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px',
    background: 'rgba(16,185,129,0.15)', color: '#10B981', border: '1px solid #10B981',
  },
  badgeOff: {
    fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px',
    background: 'rgba(100,116,139,0.15)', color: '#64748B', border: '1px solid #475569',
  },
  metricsRow: { display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' },
  metricChip: {
    display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 10px',
    background: '#0F172A', borderRadius: '12px', fontSize: '12px',
  },
  metricLabel: { color: '#CBD5E1' },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  samplingText: { fontSize: '12px', color: '#64748B' },
  actions: { display: 'flex', gap: '4px' },
  actionBtn: {
    background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer',
    padding: '4px', borderRadius: '4px',
  },
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add agent_ops_ui/src/components/evals/EvalAgentCard.tsx
git commit -m "feat(evals-tab): add EvalAgentCard summary card component"
```

---

### Task 6: EvalDetailView component

**Files:**
- Create: `agent_ops_ui/src/components/evals/EvalDetailView.tsx`

**Step 1: Create the detail view**

This component shows the per-agent eval metrics chart and config summary. It reuses the existing `EvalMetricsPanel` pattern but passes an explicit `serviceName`.

```typescript
import React, { useMemo } from 'react'
import type { EChartsOption } from 'echarts'
import EChartWrapper from '../charts/EChartWrapper'
import { useEvalMetrics } from '../../hooks/useEvalMetrics'
import type { EvalConfig, EvalMetricPoint } from '../../types'
import { ArrowLeft, Settings } from 'lucide-react'

const METRIC_COLORS: Record<string, string> = {
  coherence: '#06B6D4',
  groundedness: '#8B5CF6',
  fluency: '#10B981',
  safety: '#F59E0B',
}

function colorForMetric(name: string): string {
  return METRIC_COLORS[name.toLowerCase()] ?? '#94A3B8'
}

interface EvalDetailViewProps {
  config: EvalConfig
  hours: number
  onBack: () => void
  onEdit: (config: EvalConfig) => void
}

export default function EvalDetailView({ config, hours, onBack, onEdit }: EvalDetailViewProps) {
  const { data, isLoading } = useEvalMetrics(hours, config.agent_name)

  const option = useMemo((): EChartsOption => {
    if (!data || data.length === 0) return { series: [] }

    const byMetric: Record<string, EvalMetricPoint[]> = {}
    for (const point of data) {
      if (!byMetric[point.metricName]) byMetric[point.metricName] = []
      byMetric[point.metricName].push(point)
    }

    const allBuckets = [...new Set(data.map(p => p.timeBucket))].sort()

    const series = Object.entries(byMetric).map(([metricName, points]) => {
      const pointMap = new Map(points.map(p => [p.timeBucket, p.avgScore]))
      return {
        name: metricName.charAt(0).toUpperCase() + metricName.slice(1),
        type: 'line' as const,
        smooth: true,
        data: allBuckets.map(b => pointMap.get(b) ?? null),
        itemStyle: { color: colorForMetric(metricName) },
        lineStyle: { width: 2, color: colorForMetric(metricName) },
        symbol: 'circle',
        symbolSize: 4,
      }
    })

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: unknown) => {
          if (!Array.isArray(params)) return ''
          let header = ''
          const lines: string[] = []
          for (const p of params) {
            const param = p as { axisValueLabel?: string; marker?: string; seriesName?: string; value?: number | null }
            if (!header && param.axisValueLabel) header = param.axisValueLabel
            if (param.value != null) {
              lines.push(`${param.marker} ${param.seriesName}: <strong>${(param.value as number).toFixed(3)}</strong>`)
            }
          }
          return `<div style="font-size:12px">${header}<br/>${lines.join('<br/>')}</div>`
        },
      },
      legend: { top: 0, right: 0 },
      xAxis: {
        type: 'category',
        data: allBuckets.map(b => {
          const d = new Date(b)
          return hours <= 24
            ? d.toLocaleString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
            : d.toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })
        }),
      },
      yAxis: { type: 'value', name: 'Score', min: 0, max: 1, axisLabel: { formatter: (v: number) => v.toFixed(1) } },
      series,
    }
  }, [data, hours])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header */}
      <div style={styles.header}>
        <button style={styles.backBtn} onClick={onBack}>
          <ArrowLeft size={16} /> Back to Evaluations
        </button>
      </div>

      {/* Config summary bar */}
      <div style={styles.summaryBar}>
        <div style={styles.agentTitle}>{config.agent_name}</div>
        <div style={styles.summaryMeta}>
          <span style={config.is_enabled ? styles.badgeOn : styles.badgeOff}>
            {config.is_enabled ? 'Enabled' : 'Disabled'}
          </span>
          <span style={styles.metaText}>Sampling: {Math.round(config.sampling_rate * 100)}%</span>
          <span style={styles.metaText}>Metrics: {config.metrics.join(', ')}</span>
          <button style={styles.editBtn} onClick={() => onEdit(config)}>
            <Settings size={14} /> Edit
          </button>
        </div>
      </div>

      {/* Chart */}
      <div style={styles.chartCard}>
        <div style={styles.chartTitle}>
          <span style={styles.dot} />
          Evaluation Scores Over Time
        </div>
        <EChartWrapper option={option} loading={isLoading} height={350} />
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  header: { display: 'flex', alignItems: 'center' },
  backBtn: {
    display: 'flex', alignItems: 'center', gap: '6px', background: 'none', border: 'none',
    color: '#06B6D4', fontSize: '14px', cursor: 'pointer', padding: '4px 0',
  },
  summaryBar: {
    background: '#1E293B', border: '1px solid #334155', borderRadius: '8px', padding: '16px',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px',
  },
  agentTitle: { fontSize: '18px', fontWeight: 600, color: '#E2E8F0' },
  summaryMeta: { display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' },
  badgeOn: {
    fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px',
    background: 'rgba(16,185,129,0.15)', color: '#10B981', border: '1px solid #10B981',
  },
  badgeOff: {
    fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px',
    background: 'rgba(100,116,139,0.15)', color: '#64748B', border: '1px solid #475569',
  },
  metaText: { fontSize: '13px', color: '#94A3B8' },
  editBtn: {
    display: 'flex', alignItems: 'center', gap: '4px', background: 'none',
    border: '1px solid #334155', borderRadius: '6px', color: '#94A3B8',
    fontSize: '13px', padding: '4px 10px', cursor: 'pointer',
  },
  chartCard: {
    background: '#1E293B', border: '1px solid #334155', borderRadius: '8px', padding: '16px',
  },
  chartTitle: {
    fontSize: '13px', fontWeight: 600, color: '#78909C', textTransform: 'uppercase',
    letterSpacing: '0.5px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px',
  },
  dot: {
    display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#8B5CF6',
  },
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add agent_ops_ui/src/components/evals/EvalDetailView.tsx
git commit -m "feat(evals-tab): add EvalDetailView with metrics chart"
```

---

### Task 7: EvalsPage top-level component

**Files:**
- Create: `agent_ops_ui/src/components/evals/EvalsPage.tsx`

**Step 1: Create the page component**

```typescript
import React, { useState, useCallback } from 'react'
import { useEvalConfigs, useDeleteEvalConfig } from '../../hooks/useEvalConfigs'
import type { EvalConfig } from '../../types'
import EvalAgentCard from './EvalAgentCard'
import EvalDetailView from './EvalDetailView'
import EvalSetupWizard from './EvalSetupWizard'
import { Plus, BarChart3 } from 'lucide-react'

interface EvalsPageProps {
  hours: number
  /** Pre-selected agent (from URL param or Registry navigation). */
  initialAgent?: string
}

export default function EvalsPage({ hours, initialAgent }: EvalsPageProps) {
  const { data: configs, isLoading } = useEvalConfigs()
  const deleteMutation = useDeleteEvalConfig()

  const [selectedAgent, setSelectedAgent] = useState<string | null>(initialAgent ?? null)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [editingConfig, setEditingConfig] = useState<EvalConfig | undefined>(undefined)

  const selectedConfig = configs?.find(c => c.agent_name === selectedAgent)

  const handleSelect = useCallback((name: string) => setSelectedAgent(name), [])
  const handleBack = useCallback(() => setSelectedAgent(null), [])
  const handleEdit = useCallback((config: EvalConfig) => {
    setEditingConfig(config)
    setWizardOpen(true)
  }, [])
  const handleDelete = useCallback((name: string) => {
    if (window.confirm(`Remove evaluation config for "${name}"?`)) {
      deleteMutation.mutate(name)
      if (selectedAgent === name) setSelectedAgent(null)
    }
  }, [deleteMutation, selectedAgent])
  const handleWizardClose = useCallback(() => {
    setWizardOpen(false)
    setEditingConfig(undefined)
  }, [])
  const handleWizardSaved = useCallback((agentName: string) => {
    setSelectedAgent(agentName)
  }, [])
  const handleAddNew = useCallback(() => {
    setEditingConfig(undefined)
    setWizardOpen(true)
  }, [])

  // Detail view
  if (selectedAgent && selectedConfig) {
    return (
      <>
        <EvalDetailView
          config={selectedConfig}
          hours={hours}
          onBack={handleBack}
          onEdit={handleEdit}
        />
        <EvalSetupWizard
          isOpen={wizardOpen}
          onClose={handleWizardClose}
          existingConfig={editingConfig}
          onSaved={handleWizardSaved}
        />
      </>
    )
  }

  // List view
  return (
    <>
      {/* Header */}
      <div style={styles.pageHeader}>
        <div>
          <h2 style={styles.pageTitle}>AI Evaluations</h2>
          <p style={styles.pageSubtitle}>Monitor and configure GenAI evaluation metrics across your agents.</p>
        </div>
        <button style={styles.addBtn} onClick={handleAddNew}>
          <Plus size={16} /> Configure Agent
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div style={styles.loadingText}>Loading evaluation configs…</div>
      ) : !configs || configs.length === 0 ? (
        /* Empty state */
        <div style={styles.emptyState}>
          <BarChart3 size={48} style={{ color: '#334155' }} />
          <h3 style={styles.emptyTitle}>No evaluations configured</h3>
          <p style={styles.emptyText}>
            Set up AI evaluation to monitor coherence, groundedness, fluency, and safety scores for your agents.
          </p>
          <button style={styles.emptyCta} onClick={handleAddNew}>
            <Plus size={16} /> Set Up Your First Evaluation
          </button>
        </div>
      ) : (
        /* Agent cards grid */
        <div style={styles.grid}>
          {configs.map(config => (
            <EvalAgentCard
              key={config.agent_name}
              config={config}
              onSelect={handleSelect}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <EvalSetupWizard
        isOpen={wizardOpen}
        onClose={handleWizardClose}
        existingConfig={editingConfig}
        onSaved={handleWizardSaved}
      />
    </>
  )
}

const styles: Record<string, React.CSSProperties> = {
  pageHeader: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
    marginBottom: '24px', flexWrap: 'wrap', gap: '12px',
  },
  pageTitle: { fontSize: '20px', fontWeight: 600, color: '#E2E8F0', margin: 0 },
  pageSubtitle: { fontSize: '14px', color: '#94A3B8', margin: '4px 0 0' },
  addBtn: {
    display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px',
    background: '#06B6D4', border: 'none', borderRadius: '6px',
    color: '#0F172A', fontWeight: 600, fontSize: '14px', cursor: 'pointer',
  },
  loadingText: { color: '#94A3B8', textAlign: 'center', padding: '40px' },
  emptyState: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', padding: '80px 20px', textAlign: 'center',
  },
  emptyTitle: { fontSize: '18px', fontWeight: 600, color: '#E2E8F0', margin: '16px 0 8px' },
  emptyText: { fontSize: '14px', color: '#94A3B8', maxWidth: '400px', margin: '0 0 24px' },
  emptyCta: {
    display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 20px',
    background: '#06B6D4', border: 'none', borderRadius: '6px',
    color: '#0F172A', fontWeight: 600, fontSize: '14px', cursor: 'pointer',
  },
  grid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px',
  },
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add agent_ops_ui/src/components/evals/EvalsPage.tsx
git commit -m "feat(evals-tab): add EvalsPage with list view, empty state, and detail drill-down"
```

---

### Task 8: Wire Evals tab into App.tsx

**Files:**
- Modify: `agent_ops_ui/src/App.tsx`

**Step 1: Add import**

Add to the imports section (around line 20 where other component imports are):

```typescript
import EvalsPage from './components/evals/EvalsPage'
```

**Step 2: Add tab button**

In the tab bar JSX (after the Trajectory button, around line 393), add before the closing `</div>`:

```typescript
        <button
          style={activeTab === 'evals' ? styles.tabActive : styles.tab}
          onClick={() => {
            setFilters(prev => ({ ...prev, hours: prev.hours === 720 ? 24 : prev.hours }))
            setActiveTab('evals')
          }}
        >
          Evals
        </button>
```

**Step 3: Add conditional render**

After the trajectory render block (around line 496), add:

```typescript
{activeTab === 'evals' && (
  <EvalsPage
    hours={filters.hours}
    initialAgent={new URLSearchParams(window.location.search).get('agent') ?? undefined}
  />
)}
```

**Step 4: Add `'evals'` to the URL param validation**

In the `useState<Tab>` initializer (around line 521), the condition checks valid tab values. Add `'evals'` to that check:

```typescript
if (urlTab === 'topology' || urlTab === 'trajectory' || urlTab === 'agents' || urlTab === 'tools' || urlTab === 'dashboard' || urlTab === 'traces' || urlTab === 'logs' || urlTab === 'evals') {
```

Do the same for the `useEffect` URL sync (around line 538):

```typescript
if (tTab === 'topology' || tTab === 'trajectory' || tTab === 'agents' || tTab === 'tools' || tTab === 'dashboard' || tTab === 'traces' || tTab === 'logs' || tTab === 'evals') {
```

**Step 5: Verify TypeScript compiles**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 6: Commit**

```bash
git add agent_ops_ui/src/App.tsx
git commit -m "feat(evals-tab): wire Evals tab into App navigation"
```

---

### Task 9: Registry page "Evals" action button

**Files:**
- Modify: `agent_ops_ui/src/components/RegistryPage.tsx`

**Step 1: Add Evals icon import**

In the imports from `lucide-react` (line 11), add `BarChart3`:

```typescript
import { MessageSquare, Cpu, AlertCircle, Clock, Zap, Users, Network, Route, LayoutDashboard, List, BarChart3 } from 'lucide-react'
```

**Step 2: Add EvalSetupWizard import and state**

Add import:

```typescript
import EvalSetupWizard from './evals/EvalSetupWizard'
import { useEvalConfigs } from '../hooks/useEvalConfigs'
```

Inside the component function (after the existing state declarations), add:

```typescript
const { data: evalConfigs } = useEvalConfigs()
const [evalWizardAgent, setEvalWizardAgent] = useState<string | null>(null)
```

**Step 3: Add Evals button to `renderAgentActions`**

In the `renderAgentActions` function (around line 229), add an Evals button after the Traces button:

```typescript
const renderAgentActions = (serviceName: string) => (
  <div style={styles.actionContainer} onClick={(e) => e.stopPropagation()}>
    <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'topology')}><Network size={14} /> Graph</button>
    <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'trajectory')}><Route size={14} /> Trajectory</button>
    <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'dashboard')}><LayoutDashboard size={14} /> Dashboard</button>
    <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'traces')}><List size={14} /> Traces</button>
    <button
      style={styles.actionButton}
      onClick={() => {
        const hasConfig = evalConfigs?.some(c => c.agent_name === serviceName)
        if (hasConfig) {
          onNavigate(serviceName, 'evals')
        } else {
          setEvalWizardAgent(serviceName)
        }
      }}
    >
      <BarChart3 size={14} /> Evals
    </button>
  </div>
)
```

**Step 4: Add wizard modal render**

At the bottom of the component's return JSX (before the final closing `</div>` or fragment), add:

```typescript
<EvalSetupWizard
  isOpen={evalWizardAgent !== null}
  onClose={() => setEvalWizardAgent(null)}
  initialAgentName={evalWizardAgent ?? undefined}
  onSaved={(name) => {
    setEvalWizardAgent(null)
    onNavigate(name, 'evals')
  }}
/>
```

**Step 5: Verify TypeScript compiles**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 6: Commit**

```bash
git add agent_ops_ui/src/components/RegistryPage.tsx
git commit -m "feat(evals-tab): add Evals action button to Agent Registry cards"
```

---

### Task 10: Guest/demo mode support for eval configs

The backend returns `{ configs: [] }` for guest mode. We need the Evals tab to show something useful in demo mode instead of just an empty state.

**Files:**
- Modify: `sre_agent/api/routers/evals.py`

**Step 1: Return demo configs in guest mode**

Change the `list_eval_configs` endpoint's guest mode handler from:

```python
if is_guest_mode():
    return {"configs": []}
```

To:

```python
if is_guest_mode():
    return {
        "configs": [
            {
                "agent_name": "support-agent",
                "is_enabled": True,
                "sampling_rate": 1.0,
                "metrics": ["coherence", "groundedness", "fluency", "safety"],
                "last_eval_timestamp": None,
            },
            {
                "agent_name": "code-review-agent",
                "is_enabled": True,
                "sampling_rate": 0.5,
                "metrics": ["coherence", "groundedness"],
                "last_eval_timestamp": None,
            },
        ]
    }
```

**Step 2: Run existing tests to verify no regressions**

Run: `uv run pytest tests/unit/sre_agent/api/routers/test_evals.py -v`
Expected: The `test_list_eval_configs_guest_mode` test will fail because it expects `[]`. Update it.

**Step 3: Update the guest mode test**

In `tests/unit/sre_agent/api/routers/test_evals.py`, find `test_list_eval_configs_guest_mode` and update:

```python
def test_list_eval_configs_guest_mode(mock_guest):
    """Guest mode returns demo eval configs."""
    response = client.get("/api/v1/evals/config")
    assert response.status_code == 200
    data = response.json()
    configs = data["configs"]
    assert len(configs) == 2
    assert configs[0]["agent_name"] == "support-agent"
    assert configs[1]["agent_name"] == "code-review-agent"
```

**Step 4: Run tests to verify**

Run: `uv run pytest tests/unit/sre_agent/api/routers/test_evals.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add sre_agent/api/routers/evals.py tests/unit/sre_agent/api/routers/test_evals.py
git commit -m "feat(evals-tab): return demo eval configs in guest mode"
```

---

### Task 11: TypeScript compilation check and final verification

**Files:**
- None (verification only)

**Step 1: TypeScript check**

Run: `cd agent_ops_ui && npx tsc --noEmit`
Expected: No errors

**Step 2: Run backend tests**

Run: `uv run poe test-fast`
Expected: All pass (3565+)

**Step 3: Run linter**

Run: `uv run ruff check sre_agent/api/routers/evals.py tests/unit/sre_agent/api/routers/test_evals.py`
Expected: All checks passed

**Step 4: Push and update PR**

```bash
git push origin feat/online-genai-eval-service
```
