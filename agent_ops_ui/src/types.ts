export interface TopologyNode {
  id: string;
  type: string;
  data: {
    label: string;
    nodeType: string;
    executionCount: number;
    totalTokens: number;
    errorCount: number;
    avgDurationMs?: number;
  };
  position: { x: number; y: number };
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  data: {
    callCount: number;
    avgDurationMs: number;
    errorCount: number;
    totalTokens?: number;
  };
}

export interface TopologyResponse {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface SankeyNode {
  id: string;
  nodeColor: string;
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface SankeyResponse {
  nodes: SankeyNode[];
  links: SankeyLink[];
  loopTraces?: LoopTrace[];
}

// --- Phase 2: Detail panel types ---

export interface NodeDetail {
  nodeId: string;
  nodeType: string;
  label: string;
  totalInvocations: number;
  errorRate: number;
  errorCount: number;
  inputTokens: number;
  outputTokens: number;
  estimatedCost: number;
  latency: { p50: number; p95: number; p99: number };
  topErrors: Array<{ message: string; count: number }>;
  recentPayloads: PayloadEntry[];
}

export interface EdgeDetail {
  sourceId: string;
  targetId: string;
  callCount: number;
  errorCount: number;
  errorRate: number;
  avgDurationMs: number;
  p95DurationMs: number;
  p99DurationMs: number;
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
}

export type Tab = 'agents' | 'tools' | 'dashboard' | 'traces' | 'logs' | 'topology' | 'trajectory' | 'evals';

export type SelectedElement =
  | { kind: 'node'; id: string }
  | { kind: 'edge'; sourceId: string; targetId: string };

// --- Phase 2: Filter types ---

export interface GraphFilters {
  projectId: string;
  hours: number;
  errorsOnly: boolean;
  startTime?: string;
  endTime?: string;
  traceDataset?: string;
  serviceName?: string;
  /** Severity filter for logs tab (e.g. ['ERROR', 'WARNING']). Empty = all. */
  logSeverity?: string[];
}

// --- Phase 3: View mode and payload types ---

export type ViewMode = 'topology' | 'cost' | 'latency'

export interface PayloadEntry {
  traceId?: string
  spanId: string
  timestamp: string | null
  nodeType: string
  prompt: string | null
  completion: string | null
  toolInput: string | null
  toolOutput: string | null
}

export interface LoopInfo {
  cycle: string[]
  repetitions: number
  startIndex: number
}

export interface LoopTrace {
  traceId: string
  loops: LoopInfo[]
}

// --- Phase 4: Auto-refresh and time-series types ---

export type RefreshInterval = 30 | 60 | 300

export interface AutoRefreshConfig {
  enabled: boolean
  intervalSeconds: RefreshInterval
}

export interface TimeSeriesPoint {
  bucket: string
  callCount: number
  errorCount: number
  avgDurationMs: number
  totalTokens: number
  totalCost: number
}

export interface TimeSeriesData {
  series: Record<string, TimeSeriesPoint[]>
}

export interface SpanDetailsException {
  message: string
  stacktrace?: string
  type: string
}

export interface SpanDetails {
  traceId: string
  spanId: string
  statusCode: number
  statusMessage: string
  exceptions: SpanDetailsException[]
  evaluations?: EvalEvent[]
  attributes: Record<string, unknown>
}

export interface TraceLog {
  timestamp: string | null
  severity: string
  payload: unknown
}

export interface TraceLogsData {
  traceId: string
  logs: TraceLog[]
}

// --- Phase 5: Registry types ---

export interface RegistryAgent {
  serviceName: string
  agentId: string
  engineId?: string
  agentName: string
  description?: string
  totalSessions: number
  totalTurns: number
  inputTokens: number
  outputTokens: number
  errorCount: number
  errorRate: number
  p50DurationMs: number
  p95DurationMs: number
}

export interface AgentRegistryResponse {
  agents: RegistryAgent[]
}

export interface RegistryTool {
  serviceName: string
  toolId: string
  toolName: string
  description?: string
  executionCount: number
  errorCount: number
  errorRate: number
  avgDurationMs: number
  p95DurationMs: number
}

export interface ToolRegistryResponse {
  tools: RegistryTool[]
}

// --- Logs Explorer types ---

export interface LogEntry {
  insert_id: string
  timestamp: string
  severity: string
  payload: string | Record<string, unknown> | null
  resource_type?: string
  resource_labels?: Record<string, string>
  trace_id?: string | null
  span_id?: string | null
  http_request?: Record<string, unknown> | null
  raw?: Record<string, unknown>
}

export interface QueryLogsParams {
  filter?: string
  projectId?: string
  limit: number
  minutesAgo?: number
  cursorTimestamp?: string
  cursorInsertId?: string
}

export interface LogEntriesResponse {
  entries: LogEntry[]
  filter?: string | null
  project_id?: string | null
}

export interface HistogramBucket {
  start: string
  end: string
  debug: number
  info: number
  warning: number
  error: number
  critical: number
}

export interface LogsHistogramResponse {
  buckets: HistogramBucket[]
  total_count: number
  scanned_entries: number
  start_time: string
  end_time: string
}

export interface QueryHistogramParams {
  filter?: string
  minutesAgo?: number
  bucketCount?: number
  projectId?: string
}

// --- Evaluation types ---

export interface EvalEvent {
  metricName: string
  score: number
  explanation: string
}

export interface EvalMetricPoint {
  timeBucket: string
  metricName: string
  avgScore: number
  sampleCount: number
}

export interface EvalMetricsAggregateResponse {
  metrics: EvalMetricPoint[]
}

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
