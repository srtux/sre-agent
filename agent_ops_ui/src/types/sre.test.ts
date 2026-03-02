import { describe, it, expect } from 'vitest'
import type {
  SpanInfo,
  Trace,
  MetricPoint,
  MetricSeries,
  DashboardMetric,
  SreLogEntry,
  LogPattern,
  TimelineEvent,
  AgentTraceNode,
  CouncilSynthesisData,
  ToolLog,
  DashboardItem,
  DashboardDataType,
} from './sre'

describe('SRE domain types', () => {
  it('SpanInfo has required fields', () => {
    const span: SpanInfo = {
      spanId: 's1',
      traceId: 't1',
      name: 'test',
      startTime: '2026-01-01T00:00:00Z',
      endTime: '2026-01-01T00:00:01Z',
      attributes: {},
      status: 'OK',
    }
    expect(span.spanId).toBe('s1')
    expect(span.parentSpanId).toBeUndefined()
  })

  it('Trace contains spans', () => {
    const trace: Trace = {
      traceId: 't1',
      spans: [
        { spanId: 's1', traceId: 't1', name: 'root', startTime: '', endTime: '', attributes: {}, status: 'OK' },
      ],
    }
    expect(trace.spans).toHaveLength(1)
  })

  it('MetricPoint supports anomaly flag', () => {
    const normal: MetricPoint = { timestamp: '', value: 100 }
    const anomaly: MetricPoint = { timestamp: '', value: 999, isAnomaly: true }
    expect(normal.isAnomaly).toBeUndefined()
    expect(anomaly.isAnomaly).toBe(true)
  })

  it('MetricSeries has labels', () => {
    const series: MetricSeries = {
      metricName: 'latency',
      points: [{ timestamp: '', value: 100 }],
      labels: { service: 'api' },
    }
    expect(series.labels?.service).toBe('api')
  })

  it('DashboardMetric status is union type', () => {
    const m: DashboardMetric = {
      id: '1',
      name: 'test',
      unit: 'ms',
      currentValue: 100,
      status: 'critical',
    }
    expect(['normal', 'warning', 'critical']).toContain(m.status)
  })

  it('SreLogEntry supports JSON and string payloads', () => {
    const jsonLog: SreLogEntry = {
      insertId: '1',
      timestamp: '',
      severity: 'ERROR',
      payload: { message: 'test' },
      isJsonPayload: true,
      payloadPreview: 'test',
    }
    const stringLog: SreLogEntry = {
      insertId: '2',
      timestamp: '',
      severity: 'INFO',
      payload: 'simple text',
      isJsonPayload: false,
      payloadPreview: 'simple text',
    }
    expect(typeof jsonLog.payload).toBe('object')
    expect(typeof stringLog.payload).toBe('string')
  })

  it('LogPattern has severity counts', () => {
    const pattern: LogPattern = {
      template: 'Error: *',
      count: 42,
      severityCounts: { ERROR: 42 },
    }
    expect(pattern.severityCounts?.ERROR).toBe(42)
  })

  it('TimelineEvent type is valid union', () => {
    const event: TimelineEvent = {
      id: '1',
      timestamp: '',
      type: 'alert',
      title: 'Alert fired',
      severity: 'critical',
    }
    expect(['alert', 'deployment', 'config_change', 'scaling', 'incident', 'recovery', 'agent_action']).toContain(event.type)
  })

  it('AgentTraceNode kind is valid', () => {
    const node: AgentTraceNode = {
      spanId: 's1',
      name: 'test',
      kind: 'llm_call',
      operation: 'classify',
      startOffsetMs: 0,
      durationMs: 100,
      depth: 0,
    }
    expect(['agent_invocation', 'llm_call', 'tool_execution', 'sub_agent_delegation']).toContain(node.kind)
  })

  it('CouncilSynthesisData has mode and findings', () => {
    const council: CouncilSynthesisData = {
      title: 'RCA',
      overallConfidence: 0.9,
      findings: [{ panelName: 'trace', summary: 'test', confidence: 0.8 }],
      mode: 'standard',
    }
    expect(council.findings).toHaveLength(1)
    expect(['fast', 'standard', 'debate']).toContain(council.mode)
  })

  it('ToolLog status is valid', () => {
    const log: ToolLog = { toolName: 'test', status: 'running' }
    expect(['running', 'completed', 'error']).toContain(log.status)
  })

  it('DashboardItem has typed data fields', () => {
    const item: DashboardItem = {
      id: '1',
      type: 'traces',
      toolName: 'get_traces',
      timestamp: '',
      rawData: {},
      trace: { traceId: 't1', spans: [] },
    }
    expect(item.trace?.traceId).toBe('t1')
    expect(item.logEntries).toBeUndefined()
  })

  it('DashboardDataType covers all categories', () => {
    const types: DashboardDataType[] = [
      'traces', 'logs', 'metrics', 'alerts', 'council', 'remediation', 'analytics',
    ]
    expect(types).toHaveLength(7)
  })
})
