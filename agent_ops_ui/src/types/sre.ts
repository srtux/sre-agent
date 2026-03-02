/**
 * SRE domain types — ported from autosre/lib/models/*.dart
 * and autosre/lib/features/logs/domain/models.dart
 */

// ─── Trace Models ────────────────────────────────────────

export interface SpanInfo {
  spanId: string
  traceId: string
  name: string
  startTime: string
  endTime: string
  attributes: Record<string, unknown>
  status: string
  parentSpanId?: string | null
  duration?: number
}

export interface Trace {
  traceId: string
  spans: SpanInfo[]
}

// ─── Metric Models ───────────────────────────────────────

export interface MetricPoint {
  timestamp: string
  value: number
  isAnomaly?: boolean
}

export interface MetricSeries {
  metricName: string
  points: MetricPoint[]
  labels?: Record<string, string>
  unit?: string
}

export interface DashboardMetric {
  id: string
  name: string
  unit: string
  currentValue: number
  previousValue?: number
  threshold?: number
  status: 'normal' | 'warning' | 'critical'
  anomalyDescription?: string
}

export interface MetricsDashboardData {
  metrics: DashboardMetric[]
  lastUpdated?: string
  status?: string
}

// ─── Log Models ──────────────────────────────────────────

export interface SreLogEntry {
  insertId: string
  timestamp: string
  severity: string
  payload: string | Record<string, unknown>
  resourceLabels?: Record<string, string>
  resourceType?: string
  traceId?: string | null
  spanId?: string | null
  httpRequest?: Record<string, unknown> | null
  isJsonPayload?: boolean
  payloadPreview?: string
}

export interface LogEntriesData {
  entries: SreLogEntry[]
  filter?: string
  projectId?: string
  nextPageToken?: string | null
}

export interface LogPattern {
  template: string
  count: number
  severityCounts?: Record<string, number>
  sampleEntries?: SreLogEntry[]
}

// ─── Incident / Alert Models ─────────────────────────────

export type TimelineEventType =
  | 'alert'
  | 'deployment'
  | 'config_change'
  | 'scaling'
  | 'incident'
  | 'recovery'
  | 'agent_action'

export interface TimelineEvent {
  id: string
  timestamp: string
  type: TimelineEventType
  title: string
  description?: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  metadata?: Record<string, unknown>
  isCorrelatedToIncident?: boolean
  incidentId?: string
}

export interface IncidentTimelineData {
  title: string
  serviceName: string
  status: string
  events: TimelineEvent[]
  rootCause?: string
  timeToDetect?: string
  timeToMitigate?: string
  lastUpdated?: string
}

// ─── Agent Trace Models ──────────────────────────────────

export type AgentTraceKind =
  | 'agent_invocation'
  | 'llm_call'
  | 'tool_execution'
  | 'sub_agent_delegation'

export interface AgentTraceNode {
  spanId: string
  parentSpanId?: string | null
  name: string
  kind: AgentTraceKind
  operation: string
  startOffsetMs: number
  durationMs: number
  depth: number
  inputTokens?: number
  outputTokens?: number
  modelUsed?: string
  toolName?: string
  agentName?: string
  hasError?: boolean
}

export interface AgentTraceData {
  traceId: string
  rootAgentName: string
  nodes: AgentTraceNode[]
  totalInputTokens: number
  totalOutputTokens: number
  totalDurationMs: number
  llmCallCount: number
  toolCallCount: number
  uniqueAgents: string[]
  uniqueTools: string[]
  antiPatterns?: string[]
}

// ─── Agent Activity Graph Models ─────────────────────────

export type AgentNodeType = 'coordinator' | 'sub_agent' | 'tool' | 'data_source'
export type AgentNodeStatus = 'active' | 'completed' | 'pending' | 'error'

export interface AgentActivityNode {
  id: string
  name: string
  type: AgentNodeType
  status: AgentNodeStatus
  connections: string[]
}

export interface AgentActivityData {
  nodes: AgentActivityNode[]
  phase?: string
  currentAgent?: string
}

// ─── Agent Graph (Multi-Trace) ───────────────────────────

export interface AgentGraphNode {
  id: string
  label: string
  nodeType: string
  executionCount: number
  totalTokens: number
  errorCount: number
  avgDurationMs?: number
}

export interface AgentGraphEdge {
  source: string
  target: string
  callCount: number
  avgDurationMs: number
  errorCount: number
  totalTokens?: number
}

export interface AgentGraphData {
  nodes: AgentGraphNode[]
  edges: AgentGraphEdge[]
}

// ─── Service Topology ────────────────────────────────────

export type ServiceHealth = 'healthy' | 'degraded' | 'unhealthy'

export interface ServiceNode {
  id: string
  name: string
  health: ServiceHealth
  latency?: number
  errorRate?: number
  requestsPerSec?: number
  isIncidentSource?: boolean
}

export interface ServiceConnection {
  source: string
  target: string
  latency?: number
  errorRate?: number
  isAffectedPath?: boolean
}

export interface ServiceTopologyData {
  services: ServiceNode[]
  connections: ServiceConnection[]
  affectedPath?: string[]
}

// ─── Council / Synthesis ─────────────────────────────────

export interface PanelFinding {
  panelName: string
  summary: string
  confidence: number
  details?: string
  severity?: string
}

export interface CouncilSynthesisData {
  title: string
  overallConfidence: number
  rootCause?: string
  impact?: string
  recommendation?: string
  findings: PanelFinding[]
  mode: 'fast' | 'standard' | 'debate'
  debateRounds?: number
}

// ─── Tool Log ────────────────────────────────────────────

export type ToolLogStatus = 'running' | 'completed' | 'error'

export interface ToolLog {
  toolName: string
  args?: Record<string, unknown>
  status: ToolLogStatus
  result?: unknown
  timestamp?: string
  duration?: number
}

// ─── Vega / Analytics ────────────────────────────────────

export interface VegaChartData {
  spec: Record<string, unknown>
  data?: unknown[]
}

// ─── Remediation ─────────────────────────────────────────

export interface RemediationStep {
  command?: string
  description: string
}

export interface RemediationPlan {
  issue: string
  risk: 'low' | 'medium' | 'high'
  steps: RemediationStep[]
}

// ─── SLO ─────────────────────────────────────────────────

export interface SloBurnRate {
  sloName: string
  objective: number
  currentBurnRate: number
  budgetRemaining: number
  windows: Array<{
    duration: string
    burnRate: number
    isExhausted: boolean
  }>
}

// ─── Postmortem ──────────────────────────────────────────

export interface Postmortem {
  title: string
  severity: string
  summary: string
  timeline: Array<{ time: string; event: string }>
  rootCause: string
  impact: string
  actionItems: Array<{ description: string; owner?: string; priority?: string }>
}

// ─── Dashboard Item ──────────────────────────────────────

export type DashboardDataType =
  | 'traces'
  | 'logs'
  | 'metrics'
  | 'alerts'
  | 'council'
  | 'remediation'
  | 'analytics'

export interface DashboardItem {
  id: string
  type: DashboardDataType
  toolName: string
  timestamp: string
  rawData: unknown
  // Typed data fields — exactly one is populated
  trace?: Trace
  logEntries?: LogEntriesData
  logPatterns?: LogPattern[]
  metricSeries?: MetricSeries
  metricsDashboard?: MetricsDashboardData
  incidentTimeline?: IncidentTimelineData
  councilSynthesis?: CouncilSynthesisData
  agentActivity?: AgentActivityData
  agentTrace?: AgentTraceData
  agentGraph?: AgentGraphData
  serviceTopology?: ServiceTopologyData
  remediationPlan?: RemediationPlan
  vegaChart?: VegaChartData
  toolLog?: ToolLog
}
