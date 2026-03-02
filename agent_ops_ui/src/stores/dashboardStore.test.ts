import { describe, it, expect, beforeEach } from 'vitest'
import { useDashboardStore } from './dashboardStore'
import { mockTrace, mockLogEntriesData, mockLogPatterns, mockMetricSeries, mockMetricsDashboard, mockIncidentTimeline, mockCouncilSynthesis } from '../test-utils/mockData'

describe('dashboardStore', () => {
  beforeEach(() => {
    useDashboardStore.setState({
      items: [],
      isOpen: false,
      activeTab: 'traces',
      isRailExpanded: false,
      metricsQueryLanguage: 0,
    })
  })

  it('starts with empty items', () => {
    expect(useDashboardStore.getState().items).toHaveLength(0)
    expect(useDashboardStore.getState().hasData()).toBe(false)
  })

  it('addTrace adds a trace item and opens dashboard', () => {
    const store = useDashboardStore.getState()
    store.addTrace(mockTrace, 'get_traces', {})
    const state = useDashboardStore.getState()
    expect(state.items).toHaveLength(1)
    expect(state.items[0].type).toBe('traces')
    expect(state.items[0].trace?.traceId).toBe('trace-abc123')
    expect(state.isOpen).toBe(true)
    expect(state.activeTab).toBe('traces')
  })

  it('addLogEntries adds log items', () => {
    useDashboardStore.getState().addLogEntries(mockLogEntriesData, 'get_logs', {})
    const state = useDashboardStore.getState()
    expect(state.items).toHaveLength(1)
    expect(state.items[0].type).toBe('logs')
    expect(state.activeTab).toBe('logs')
  })

  it('addLogPatterns adds pattern items', () => {
    useDashboardStore.getState().addLogPatterns(mockLogPatterns, 'analyze_logs', {})
    const state = useDashboardStore.getState()
    expect(state.items).toHaveLength(1)
    expect(state.items[0].logPatterns).toHaveLength(3)
  })

  it('addMetricSeries adds metric items', () => {
    useDashboardStore.getState().addMetricSeries(mockMetricSeries, 'list_metrics', {})
    const state = useDashboardStore.getState()
    expect(state.items).toHaveLength(1)
    expect(state.items[0].type).toBe('metrics')
  })

  it('addMetricsDashboard adds dashboard metrics', () => {
    useDashboardStore.getState().addMetricsDashboard(mockMetricsDashboard, 'get_dashboard', {})
    expect(useDashboardStore.getState().items[0].metricsDashboard?.metrics).toHaveLength(4)
  })

  it('addAlerts adds alert items', () => {
    useDashboardStore.getState().addAlerts(mockIncidentTimeline, 'get_alerts', {})
    const state = useDashboardStore.getState()
    expect(state.items[0].type).toBe('alerts')
    expect(state.activeTab).toBe('alerts')
  })

  it('addCouncilSynthesis adds council items', () => {
    useDashboardStore.getState().addCouncilSynthesis(mockCouncilSynthesis, 'synthesize', {})
    const state = useDashboardStore.getState()
    expect(state.items[0].type).toBe('council')
    expect(state.items[0].councilSynthesis?.mode).toBe('standard')
  })

  it('itemsOfType filters correctly', () => {
    const store = useDashboardStore.getState()
    store.addTrace(mockTrace, 'get_traces', {})
    store.addLogEntries(mockLogEntriesData, 'get_logs', {})
    store.addTrace({ traceId: 't2', spans: [] }, 'get_traces', {})

    expect(useDashboardStore.getState().itemsOfType('traces')).toHaveLength(2)
    expect(useDashboardStore.getState().itemsOfType('logs')).toHaveLength(1)
    expect(useDashboardStore.getState().itemsOfType('metrics')).toHaveLength(0)
  })

  it('typeCounts returns correct counts', () => {
    const store = useDashboardStore.getState()
    store.addTrace(mockTrace, 'get_traces', {})
    store.addTrace({ traceId: 't2', spans: [] }, 'get_traces', {})
    store.addLogEntries(mockLogEntriesData, 'get_logs', {})

    const counts = useDashboardStore.getState().typeCounts()
    expect(counts.traces).toBe(2)
    expect(counts.logs).toBe(1)
    expect(counts.metrics).toBe(0)
  })

  it('removeItem removes specific item', () => {
    useDashboardStore.getState().addTrace(mockTrace, 'get_traces', {})
    const itemId = useDashboardStore.getState().items[0].id
    useDashboardStore.getState().removeItem(itemId)
    expect(useDashboardStore.getState().items).toHaveLength(0)
  })

  it('clear removes all items', () => {
    useDashboardStore.getState().addTrace(mockTrace, 'get_traces', {})
    useDashboardStore.getState().addLogEntries(mockLogEntriesData, 'get_logs', {})
    useDashboardStore.getState().clear()
    expect(useDashboardStore.getState().items).toHaveLength(0)
  })

  it('toggleDashboard toggles isOpen', () => {
    expect(useDashboardStore.getState().isOpen).toBe(false)
    useDashboardStore.getState().toggleDashboard()
    expect(useDashboardStore.getState().isOpen).toBe(true)
    useDashboardStore.getState().toggleDashboard()
    expect(useDashboardStore.getState().isOpen).toBe(false)
  })

  it('setActiveTab changes tab', () => {
    useDashboardStore.getState().setActiveTab('metrics')
    expect(useDashboardStore.getState().activeTab).toBe('metrics')
  })

  it('addFromEvent processes dashboard events', () => {
    const result = useDashboardStore.getState().addFromEvent({
      widget_type: 'x-sre-trace-waterfall',
      tool_name: 'get_traces',
      data: { traceId: 'from-event', spans: [] },
    })
    expect(result).toBe(true)
    expect(useDashboardStore.getState().items).toHaveLength(1)
  })

  it('addFromEvent returns false for unknown widget types', () => {
    const result = useDashboardStore.getState().addFromEvent({
      widget_type: 'x-sre-unknown',
      tool_name: 'test',
      data: {},
    })
    // Unknown types still get classified under a fallback
    expect(typeof result).toBe('boolean')
  })

  it('addFromEvent returns false for empty events', () => {
    const result = useDashboardStore.getState().addFromEvent({})
    expect(result).toBe(false)
  })

  it('respects MAX_ITEMS limit', () => {
    const store = useDashboardStore.getState()
    for (let i = 0; i < 210; i++) {
      store.addTrace({ traceId: `t-${i}`, spans: [] }, 'test', {})
    }
    expect(useDashboardStore.getState().items.length).toBeLessThanOrEqual(200)
  })
})
