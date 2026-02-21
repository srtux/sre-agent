import { useQuery } from '@tanstack/react-query'
import { useDashboardFilters } from '../contexts/DashboardFilterContext'

// --- Types ---

export interface ModelCallRow {
  modelName: string
  totalCalls: number
  p95Duration: number
  errorRate: number
  quotaExits: number
  tokensUsed: number
}

export interface ToolCallRow {
  toolName: string
  totalCalls: number
  p95Duration: number
  errorRate: number
}

export type LogSeverity = 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'

export interface AgentLogRow {
  timestamp: string
  agentId: string
  severity: LogSeverity
  message: string
  traceId: string
}

export interface DashboardTablesData {
  modelCalls: ModelCallRow[]
  toolCalls: ToolCallRow[]
  agentLogs: AgentLogRow[]
}

// --- Mock data generators ---

const MODEL_NAMES = [
  'gemini-2.5-flash',
  'gemini-2.5-pro',
  'gemini-2.0-flash',
  'gemini-1.5-pro',
  'gemini-1.5-flash',
  'claude-3.5-sonnet',
  'gpt-4o',
  'gpt-4o-mini',
]

const TOOL_NAMES = [
  'fetch_traces',
  'fetch_logs',
  'query_metrics',
  'list_alert_policies',
  'analyze_slo_burn_rate',
  'search_google',
  'fetch_web_page',
  'get_trace_details',
  'list_gke_clusters',
  'run_bigquery_sql',
  'get_metric_descriptors',
  'create_github_pr',
  'execute_playbook',
  'discover_telemetry_sources',
  'correlate_signals',
]

const AGENT_IDS = [
  'root-orchestrator',
  'trace-analyst',
  'log-analyst',
  'metrics-analyst',
  'alert-analyst',
  'root-cause-analyst',
  'council-synthesizer',
  'council-critic',
]

const LOG_MESSAGES = [
  'Starting investigation for incident INC-4821',
  'Fetched 2,450 trace spans from Cloud Trace API',
  'Anomaly detected: p95 latency spike of 340% above baseline',
  'Council mode activated: DEBATE (severity=high)',
  'Panel trace-analyst completed analysis in 2.3s',
  'Token budget 80% consumed, switching to fast model',
  'Circuit breaker OPEN for tool fetch_metrics after 3 failures',
  'SLO burn rate exceeding threshold: 2.4x on error-rate SLO',
  'Correlation found between deploy event and latency spike',
  'MCP fallback: BigQuery query timeout, using direct API',
  'Root cause hypothesis: memory leak in checkout-service v2.14.0',
  'Remediation suggestion: rollback checkout-service to v2.13.2',
  'Session context compacted: 45,000 tokens reduced to 12,000',
  'Synthesizer merged findings from 5 panels with confidence 0.87',
  'Critic challenge round 2: questioning trace-analyst conclusion',
  'Alert policy violation: error_rate > 5% for frontend-service',
  'GKE cluster node-pool-1 showing high CPU utilization (92%)',
  'BigQuery query completed: scanned 2.1 GB in 4.2s',
  'Playbook gke-troubleshoot step 3/7: checking pod status',
  'Investigation complete: RCA confidence 0.91, severity P2',
]

const SEVERITIES: LogSeverity[] = ['INFO', 'WARNING', 'ERROR', 'DEBUG']
const SEVERITY_WEIGHTS = [0.6, 0.2, 0.1, 0.1]

function seededRandom(seed: number): () => number {
  let state = seed
  return () => {
    state = (state * 1664525 + 1013904223) & 0xffffffff
    return (state >>> 0) / 0xffffffff
  }
}

function weightedChoice<T>(items: T[], weights: number[], rand: () => number): T {
  const total = weights.reduce((a, b) => a + b, 0)
  let r = rand() * total
  for (let i = 0; i < items.length; i++) {
    r -= weights[i]
    if (r <= 0) return items[i]
  }
  return items[items.length - 1]
}

const timeRangeToMs: Record<string, number> = {
  '1h': 60 * 60 * 1000,
  '6h': 6 * 60 * 60 * 1000,
  '24h': 24 * 60 * 60 * 1000,
  '7d': 7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
}

function generateModelCalls(rand: () => number): ModelCallRow[] {
  const count = 1000 + Math.floor(rand() * 200)
  const rows: ModelCallRow[] = []
  for (let i = 0; i < count; i++) {
    const modelName = MODEL_NAMES[Math.floor(rand() * MODEL_NAMES.length)]
    rows.push({
      modelName,
      totalCalls: Math.floor(rand() * 5000) + 10,
      p95Duration: Math.floor(rand() * 4000) + 100,
      errorRate: Math.round(rand() * 15 * 100) / 100,
      quotaExits: Math.floor(rand() * 50),
      tokensUsed: Math.floor(rand() * 500000) + 1000,
    })
  }
  return rows
}

function generateToolCalls(rand: () => number): ToolCallRow[] {
  const count = 1200 + Math.floor(rand() * 300)
  const rows: ToolCallRow[] = []
  for (let i = 0; i < count; i++) {
    const toolName = TOOL_NAMES[Math.floor(rand() * TOOL_NAMES.length)]
    rows.push({
      toolName,
      totalCalls: Math.floor(rand() * 8000) + 5,
      p95Duration: Math.floor(rand() * 3000) + 50,
      errorRate: Math.round(rand() * 12 * 100) / 100,
    })
  }
  return rows
}

// TODO: filter by selectedAgents when connected to real API
function generateAgentLogs(
  rand: () => number,
  durationMs: number,
): AgentLogRow[] {
  const count = 1500 + Math.floor(rand() * 500)
  const now = Date.now()
  const rows: AgentLogRow[] = []
  for (let i = 0; i < count; i++) {
    const offset = Math.floor(rand() * durationMs)
    const ts = new Date(now - offset)
    rows.push({
      timestamp: ts.toISOString(),
      agentId: AGENT_IDS[Math.floor(rand() * AGENT_IDS.length)],
      severity: weightedChoice(SEVERITIES, SEVERITY_WEIGHTS, rand),
      message: LOG_MESSAGES[Math.floor(rand() * LOG_MESSAGES.length)],
      traceId: Array.from({ length: 32 }, () =>
        Math.floor(rand() * 16).toString(16),
      ).join(''),
    })
  }
  // Sort newest first
  rows.sort((a, b) => b.timestamp.localeCompare(a.timestamp))
  return rows
}

async function fetchDashboardTables(
  timeRange: string,
  selectedAgents: string[],
): Promise<DashboardTablesData> {
  // Simulate network latency
  await new Promise((resolve) => setTimeout(resolve, 300))

  const seed =
    Array.from(timeRange).reduce((acc, ch) => acc * 31 + ch.charCodeAt(0), 0) +
    selectedAgents.length +
    17
  const rand = seededRandom(seed)
  const durationMs = timeRangeToMs[timeRange] ?? timeRangeToMs['24h']

  return {
    modelCalls: generateModelCalls(rand),
    toolCalls: generateToolCalls(rand),
    agentLogs: generateAgentLogs(rand, durationMs),
  }
}

// --- Hook ---

export function useDashboardTables() {
  const { timeRange, selectedAgents } = useDashboardFilters()

  return useQuery({
    queryKey: ['dashboard-tables', timeRange, selectedAgents],
    queryFn: () => fetchDashboardTables(timeRange, selectedAgents),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}
