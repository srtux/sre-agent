/**
 * Sample data for component tests.
 */
import type {
  Trace,
  SpanInfo,
  MetricSeries,
  MetricPoint,
  MetricsDashboardData,
  DashboardMetric,
  SreLogEntry,
  LogEntriesData,
  LogPattern,
  IncidentTimelineData,
  TimelineEvent,
  CouncilSynthesisData,
  PanelFinding,
  AgentActivityData,
  AgentTraceData,
  AgentGraphData,
  ToolLog,
  RemediationPlan,
  ServiceTopologyData,
  Postmortem,
  SloBurnRate,
} from '../types/sre'

// ─── Traces ──────────────────────────────────────────────

export const mockSpans: SpanInfo[] = [
  {
    spanId: 'span-001',
    traceId: 'trace-abc123',
    name: 'HTTP GET /api/users',
    startTime: '2026-03-01T10:00:00.000Z',
    endTime: '2026-03-01T10:00:00.250Z',
    attributes: { 'http.method': 'GET', 'http.status_code': 200 },
    status: 'OK',
    parentSpanId: null,
    duration: 250,
  },
  {
    spanId: 'span-002',
    traceId: 'trace-abc123',
    name: 'DB Query: SELECT users',
    startTime: '2026-03-01T10:00:00.050Z',
    endTime: '2026-03-01T10:00:00.180Z',
    attributes: { 'db.system': 'postgresql' },
    status: 'OK',
    parentSpanId: 'span-001',
    duration: 130,
  },
  {
    spanId: 'span-003',
    traceId: 'trace-abc123',
    name: 'Cache Lookup',
    startTime: '2026-03-01T10:00:00.010Z',
    endTime: '2026-03-01T10:00:00.040Z',
    attributes: { 'cache.hit': false },
    status: 'OK',
    parentSpanId: 'span-001',
    duration: 30,
  },
]

export const mockTrace: Trace = {
  traceId: 'trace-abc123',
  spans: mockSpans,
}

// ─── Metrics ─────────────────────────────────────────────

export const mockMetricPoints: MetricPoint[] = Array.from({ length: 24 }, (_, i) => ({
  timestamp: new Date(Date.now() - (23 - i) * 3600_000).toISOString(),
  value: 100 + Math.sin(i / 4) * 50 + Math.random() * 10,
  isAnomaly: i === 18,
}))

export const mockMetricSeries: MetricSeries = {
  metricName: 'request_latency_ms',
  points: mockMetricPoints,
  labels: { service: 'api-gateway' },
  unit: 'ms',
}

export const mockDashboardMetrics: DashboardMetric[] = [
  { id: 'm1', name: 'Request Rate', unit: 'req/s', currentValue: 1250, previousValue: 1100, status: 'normal' },
  { id: 'm2', name: 'Error Rate', unit: '%', currentValue: 2.5, previousValue: 0.5, threshold: 1, status: 'critical', anomalyDescription: 'Spike in 5xx errors' },
  { id: 'm3', name: 'P99 Latency', unit: 'ms', currentValue: 850, previousValue: 200, threshold: 500, status: 'warning' },
  { id: 'm4', name: 'CPU Usage', unit: '%', currentValue: 45, previousValue: 42, status: 'normal' },
]

export const mockMetricsDashboard: MetricsDashboardData = {
  metrics: mockDashboardMetrics,
  lastUpdated: new Date().toISOString(),
  status: 'warning',
}

// ─── Logs ────────────────────────────────────────────────

export const mockLogEntries: SreLogEntry[] = [
  {
    insertId: 'log-001',
    timestamp: '2026-03-01T10:00:01.000Z',
    severity: 'ERROR',
    payload: { message: 'Connection refused to database host', error_code: 'ECONNREFUSED' },
    resourceType: 'gce_instance',
    resourceLabels: { instance_id: 'i-12345' },
    isJsonPayload: true,
    payloadPreview: 'Connection refused to database host',
  },
  {
    insertId: 'log-002',
    timestamp: '2026-03-01T10:00:02.000Z',
    severity: 'WARNING',
    payload: 'High memory usage detected: 92%',
    resourceType: 'gke_container',
    isJsonPayload: false,
    payloadPreview: 'High memory usage detected: 92%',
  },
  {
    insertId: 'log-003',
    timestamp: '2026-03-01T10:00:03.000Z',
    severity: 'INFO',
    payload: { message: 'Request completed successfully', latency_ms: 150 },
    resourceType: 'cloud_run_revision',
    isJsonPayload: true,
    payloadPreview: 'Request completed successfully',
  },
]

export const mockLogEntriesData: LogEntriesData = {
  entries: mockLogEntries,
  filter: 'severity >= WARNING',
  projectId: 'test-project',
}

export const mockLogPatterns: LogPattern[] = [
  { template: 'Connection refused to * host', count: 42, severityCounts: { ERROR: 42 } },
  { template: 'High memory usage detected: *%', count: 15, severityCounts: { WARNING: 15 } },
  { template: 'Request completed successfully', count: 1200, severityCounts: { INFO: 1200 } },
]

// ─── Incidents / Alerts ──────────────────────────────────

export const mockTimelineEvents: TimelineEvent[] = [
  { id: 'evt-1', timestamp: '2026-03-01T09:45:00.000Z', type: 'alert', title: 'High error rate alert fired', severity: 'critical', description: 'Error rate exceeded 5% threshold' },
  { id: 'evt-2', timestamp: '2026-03-01T09:50:00.000Z', type: 'deployment', title: 'v2.3.1 deployed', severity: 'info', description: 'New version deployed to production' },
  { id: 'evt-3', timestamp: '2026-03-01T10:00:00.000Z', type: 'incident', title: 'Database connection failures', severity: 'high' },
  { id: 'evt-4', timestamp: '2026-03-01T10:15:00.000Z', type: 'agent_action', title: 'AutoSRE investigating', severity: 'info' },
  { id: 'evt-5', timestamp: '2026-03-01T10:30:00.000Z', type: 'recovery', title: 'Connection pool reset', severity: 'medium' },
]

export const mockIncidentTimeline: IncidentTimelineData = {
  title: 'Database Connection Storm',
  serviceName: 'api-gateway',
  status: 'mitigated',
  events: mockTimelineEvents,
  rootCause: 'Connection pool exhaustion due to leaked connections in v2.3.1',
  timeToDetect: '5 minutes',
  timeToMitigate: '45 minutes',
}

// ─── Council ─────────────────────────────────────────────

export const mockPanelFindings: PanelFinding[] = [
  { panelName: 'Trace Analysis', summary: 'Elevated latency in DB calls', confidence: 0.85, severity: 'high' },
  { panelName: 'Log Analysis', summary: 'Connection refused errors correlate with deployment', confidence: 0.92, severity: 'critical' },
  { panelName: 'Metrics Analysis', summary: 'Error rate spike began at 09:50 UTC', confidence: 0.88, severity: 'high' },
  { panelName: 'Alert Analysis', summary: 'Critical alert matches error pattern', confidence: 0.95, severity: 'critical' },
]

export const mockCouncilSynthesis: CouncilSynthesisData = {
  title: 'Root Cause Analysis: API Gateway Degradation',
  overallConfidence: 0.91,
  rootCause: 'Connection pool leak in v2.3.1 causing database connection exhaustion',
  impact: 'Elevated 5xx errors affecting ~15% of API requests',
  recommendation: 'Roll back to v2.3.0 and fix connection leak before re-deploying',
  findings: mockPanelFindings,
  mode: 'standard',
}

// ─── Agent Activity ──────────────────────────────────────

export const mockAgentActivity: AgentActivityData = {
  nodes: [
    { id: 'coord', name: 'Coordinator', type: 'coordinator', status: 'completed', connections: ['trace', 'logs', 'metrics'] },
    { id: 'trace', name: 'Trace Analyst', type: 'sub_agent', status: 'completed', connections: ['trace-api'] },
    { id: 'logs', name: 'Log Analyst', type: 'sub_agent', status: 'active', connections: ['logs-api'] },
    { id: 'metrics', name: 'Metrics Analyst', type: 'sub_agent', status: 'pending', connections: ['metrics-api'] },
    { id: 'trace-api', name: 'Cloud Trace', type: 'data_source', status: 'completed', connections: [] },
    { id: 'logs-api', name: 'Cloud Logging', type: 'data_source', status: 'active', connections: [] },
    { id: 'metrics-api', name: 'Cloud Monitoring', type: 'data_source', status: 'pending', connections: [] },
  ],
  phase: 'Analyzing logs',
  currentAgent: 'logs',
}

// ─── Agent Trace ─────────────────────────────────────────

export const mockAgentTrace: AgentTraceData = {
  traceId: 'agent-trace-001',
  rootAgentName: 'sre-agent',
  nodes: [
    { spanId: 'at-1', name: 'sre-agent', kind: 'agent_invocation', operation: 'investigate', startOffsetMs: 0, durationMs: 5000, depth: 0, inputTokens: 500, outputTokens: 200, agentName: 'sre-agent' },
    { spanId: 'at-2', parentSpanId: 'at-1', name: 'classify_intent', kind: 'llm_call', operation: 'classify', startOffsetMs: 100, durationMs: 800, depth: 1, inputTokens: 200, outputTokens: 50, modelUsed: 'gemini-2.5-flash' },
    { spanId: 'at-3', parentSpanId: 'at-1', name: 'get_traces', kind: 'tool_execution', operation: 'tool', startOffsetMs: 1000, durationMs: 1200, depth: 1, toolName: 'get_traces' },
    { spanId: 'at-4', parentSpanId: 'at-1', name: 'trace-analyst', kind: 'sub_agent_delegation', operation: 'delegate', startOffsetMs: 2500, durationMs: 2000, depth: 1, agentName: 'trace-analyst' },
  ],
  totalInputTokens: 700,
  totalOutputTokens: 250,
  totalDurationMs: 5000,
  llmCallCount: 1,
  toolCallCount: 1,
  uniqueAgents: ['sre-agent', 'trace-analyst'],
  uniqueTools: ['get_traces'],
}

// ─── Agent Graph ─────────────────────────────────────────

export const mockAgentGraph: AgentGraphData = {
  nodes: [
    { id: 'root', label: 'sre-agent', nodeType: 'root', executionCount: 100, totalTokens: 50000, errorCount: 2 },
    { id: 'trace', label: 'trace-analyst', nodeType: 'sub_agent', executionCount: 80, totalTokens: 20000, errorCount: 1 },
    { id: 'logs', label: 'log-analyst', nodeType: 'sub_agent', executionCount: 75, totalTokens: 18000, errorCount: 0 },
  ],
  edges: [
    { source: 'root', target: 'trace', callCount: 80, avgDurationMs: 2000, errorCount: 1 },
    { source: 'root', target: 'logs', callCount: 75, avgDurationMs: 1500, errorCount: 0 },
  ],
}

// ─── Service Topology ────────────────────────────────────

export const mockServiceTopology: ServiceTopologyData = {
  services: [
    { id: 'gw', name: 'api-gateway', health: 'degraded', latency: 850, errorRate: 2.5, requestsPerSec: 1250, isIncidentSource: true },
    { id: 'auth', name: 'auth-service', health: 'healthy', latency: 50, errorRate: 0.1, requestsPerSec: 800 },
    { id: 'db', name: 'cloud-sql', health: 'unhealthy', latency: 5000, errorRate: 15, requestsPerSec: 500 },
  ],
  connections: [
    { source: 'gw', target: 'auth', latency: 50 },
    { source: 'gw', target: 'db', latency: 5000, errorRate: 15, isAffectedPath: true },
  ],
  affectedPath: ['gw', 'db'],
}

// ─── Tool Log ────────────────────────────────────────────

export const mockToolLog: ToolLog = {
  toolName: 'get_traces',
  args: { project_id: 'test-project', filter: 'latency > 500ms' },
  status: 'completed',
  result: { trace_count: 42 },
  timestamp: new Date().toISOString(),
  duration: 1250,
}

// ─── Remediation ─────────────────────────────────────────

export const mockRemediationPlan: RemediationPlan = {
  issue: 'Database connection pool exhaustion',
  risk: 'medium',
  steps: [
    { description: 'Check current connection pool stats', command: 'gcloud sql instances describe my-instance --format="json(settings.databaseFlags)"' },
    { description: 'Increase max connections', command: 'gcloud sql instances patch my-instance --database-flags max_connections=200' },
    { description: 'Restart affected pods', command: 'kubectl rollout restart deployment/api-gateway -n production' },
  ],
}

// ─── Postmortem ──────────────────────────────────────────

export const mockPostmortem: Postmortem = {
  title: 'API Gateway Outage — March 1, 2026',
  severity: 'P1',
  summary: 'Database connection pool leak in v2.3.1 caused cascading failures across the API gateway.',
  timeline: [
    { time: '09:50 UTC', event: 'v2.3.1 deployed to production' },
    { time: '09:55 UTC', event: 'Error rate begins increasing' },
    { time: '10:00 UTC', event: 'Critical alert fires' },
    { time: '10:30 UTC', event: 'Connection pool reset applied' },
  ],
  rootCause: 'Connection pool leak introduced in v2.3.1 database migration code.',
  impact: '15% of API requests returned 5xx errors for 40 minutes.',
  actionItems: [
    { description: 'Add connection pool monitoring', owner: 'Platform Team', priority: 'P0' },
    { description: 'Add integration test for connection lifecycle', owner: 'API Team', priority: 'P1' },
  ],
}

// ─── SLO Burn Rate ───────────────────────────────────────

export const mockSloBurnRate: SloBurnRate = {
  sloName: 'API Availability',
  objective: 99.9,
  currentBurnRate: 2.5,
  budgetRemaining: 45,
  windows: [
    { duration: '1h', burnRate: 5.0, isExhausted: false },
    { duration: '6h', burnRate: 2.5, isExhausted: false },
    { duration: '24h', burnRate: 1.2, isExhausted: false },
  ],
}
