/**
 * Dashboard state store (Zustand).
 * Manages dashboard items by type, active tab, and panel state.
 * Ported from autosre/lib/services/dashboard_state.dart (~873 lines)
 */
import { create } from 'zustand'
import type {
  DashboardDataType,
  DashboardItem,
  Trace,
  LogEntriesData,
  LogPattern,
  MetricSeries,
  MetricsDashboardData,
  IncidentTimelineData,
  CouncilSynthesisData,
  AgentActivityData,
  AgentTraceData,
  AgentGraphData,
  ServiceTopologyData,
  RemediationPlan,
  VegaChartData,
} from '../types/sre'

const MAX_ITEMS = 200

/** Classify x-sre-* component type to dashboard data type. */
function classifyComponent(widgetType: string): DashboardDataType | null {
  switch (widgetType) {
    case 'x-sre-trace-waterfall':
      return 'traces'
    case 'x-sre-log-entries-viewer':
    case 'x-sre-log-pattern-viewer':
      return 'logs'
    case 'x-sre-metric-chart':
    case 'x-sre-metrics-dashboard':
      return 'metrics'
    case 'x-sre-incident-timeline':
      return 'alerts'
    case 'x-sre-council-synthesis':
    case 'x-sre-agent-activity':
    case 'x-sre-agent-trace':
    case 'x-sre-agent-graph':
    case 'x-sre-service-topology':
      return 'council'
    case 'x-sre-vega-chart':
      return 'analytics'
    default:
      return null
  }
}

export type DataSource = 'agent' | 'manual'

interface DashboardState {
  items: DashboardItem[]
  isOpen: boolean
  activeTab: DashboardDataType
  isRailExpanded: boolean
  metricsQueryLanguage: number

  // Actions
  addItem: (item: DashboardItem) => void
  removeItem: (id: string) => void
  clear: () => void
  clearManualItems: () => void

  // Panel state
  toggleDashboard: () => void
  openDashboard: () => void
  closeDashboard: () => void
  setActiveTab: (tab: DashboardDataType) => void
  toggleRail: () => void
  setMetricsQueryLanguage: (index: number) => void

  // Typed data addition methods
  addTrace: (trace: Trace, toolName: string, raw: unknown) => void
  addLogEntries: (data: LogEntriesData, toolName: string, raw: unknown) => void
  addLogPatterns: (patterns: LogPattern[], toolName: string, raw: unknown) => void
  addMetricSeries: (series: MetricSeries, toolName: string, raw: unknown) => void
  addMetricsDashboard: (data: MetricsDashboardData, toolName: string, raw: unknown) => void
  addAlerts: (data: IncidentTimelineData, toolName: string, raw: unknown) => void
  addCouncilSynthesis: (data: CouncilSynthesisData, toolName: string, raw: unknown) => void
  addRemediation: (plan: RemediationPlan, toolName: string, raw: unknown) => void
  addChart: (data: VegaChartData, toolName: string, raw: unknown) => void

  // Event processing — primary API for data ingestion from NDJSON stream
  addFromEvent: (event: Record<string, unknown>) => boolean

  // Getters (as functions since Zustand doesn't support computed)
  itemsOfType: (type: DashboardDataType) => DashboardItem[]
  typeCounts: () => Record<DashboardDataType, number>
  hasData: () => boolean
}

let itemCounter = 0
function generateItemId(): string {
  return `dash-${Date.now()}-${++itemCounter}`
}

function createItem(
  type: DashboardDataType,
  toolName: string,
  raw: unknown,
  overrides: Partial<DashboardItem> = {},
): DashboardItem {
  return {
    id: generateItemId(),
    type,
    toolName,
    timestamp: new Date().toISOString(),
    rawData: raw,
    ...overrides,
  }
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  items: [],
  isOpen: false,
  activeTab: 'traces',
  isRailExpanded: false,
  metricsQueryLanguage: 0,

  addItem: (item) =>
    set((state) => {
      const items = [item, ...state.items].slice(0, MAX_ITEMS)
      return { items, isOpen: true }
    }),

  removeItem: (id) =>
    set((state) => ({
      items: state.items.filter((i) => i.id !== id),
    })),

  clear: () => set({ items: [] }),
  clearManualItems: () =>
    set((state) => ({
      items: state.items,
    })),

  toggleDashboard: () => set((state) => ({ isOpen: !state.isOpen })),
  openDashboard: () => set({ isOpen: true }),
  closeDashboard: () => set({ isOpen: false }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  toggleRail: () => set((state) => ({ isRailExpanded: !state.isRailExpanded })),
  setMetricsQueryLanguage: (index) => set({ metricsQueryLanguage: index }),

  addTrace: (trace, toolName, raw) => {
    const item = createItem('traces', toolName, raw, { trace })
    get().addItem(item)
    set({ activeTab: 'traces' })
  },

  addLogEntries: (data, toolName, raw) => {
    const item = createItem('logs', toolName, raw, { logEntries: data })
    get().addItem(item)
    set({ activeTab: 'logs' })
  },

  addLogPatterns: (patterns, toolName, raw) => {
    const item = createItem('logs', toolName, raw, { logPatterns: patterns })
    get().addItem(item)
    set({ activeTab: 'logs' })
  },

  addMetricSeries: (series, toolName, raw) => {
    const item = createItem('metrics', toolName, raw, { metricSeries: series })
    get().addItem(item)
    set({ activeTab: 'metrics' })
  },

  addMetricsDashboard: (data, toolName, raw) => {
    const item = createItem('metrics', toolName, raw, { metricsDashboard: data })
    get().addItem(item)
    set({ activeTab: 'metrics' })
  },

  addAlerts: (data, toolName, raw) => {
    const item = createItem('alerts', toolName, raw, { incidentTimeline: data })
    get().addItem(item)
    set({ activeTab: 'alerts' })
  },

  addCouncilSynthesis: (data, toolName, raw) => {
    const item = createItem('council', toolName, raw, { councilSynthesis: data })
    get().addItem(item)
    set({ activeTab: 'council' })
  },

  addRemediation: (plan, toolName, raw) => {
    const item = createItem('remediation', toolName, raw, { remediationPlan: plan })
    get().addItem(item)
  },

  addChart: (data, toolName, raw) => {
    const item = createItem('analytics', toolName, raw, { vegaChart: data })
    get().addItem(item)
    set({ activeTab: 'analytics' })
  },

  addFromEvent: (event) => {
    const widgetType = event.widget_type as string | undefined
    const toolName = (event.tool_name as string) || 'unknown'
    const data = (event.data as Record<string, unknown>) || {}
    const category = event.category as string | undefined

    if (!widgetType && !category) return false

    const dashType = widgetType
      ? classifyComponent(widgetType)
      : (category as DashboardDataType | undefined) ?? null

    if (!dashType) return false

    switch (widgetType) {
      case 'x-sre-trace-waterfall':
        get().addTrace(data as unknown as Trace, toolName, event)
        return true
      case 'x-sre-log-entries-viewer':
        get().addLogEntries(data as unknown as LogEntriesData, toolName, event)
        return true
      case 'x-sre-log-pattern-viewer':
        get().addLogPatterns(
          (data.patterns as LogPattern[]) || [],
          toolName,
          event,
        )
        return true
      case 'x-sre-metric-chart':
        get().addMetricSeries(data as unknown as MetricSeries, toolName, event)
        return true
      case 'x-sre-metrics-dashboard':
        get().addMetricsDashboard(
          data as unknown as MetricsDashboardData,
          toolName,
          event,
        )
        return true
      case 'x-sre-incident-timeline':
        get().addAlerts(
          data as unknown as IncidentTimelineData,
          toolName,
          event,
        )
        return true
      case 'x-sre-council-synthesis':
        get().addCouncilSynthesis(
          data as unknown as CouncilSynthesisData,
          toolName,
          event,
        )
        return true
      case 'x-sre-vega-chart':
        get().addChart(data as unknown as VegaChartData, toolName, event)
        return true
      default: {
        // Fallback: create a generic item for the classified type
        const item = createItem(dashType, toolName, event, {
          agentActivity: widgetType === 'x-sre-agent-activity' ? (data as unknown as AgentActivityData) : undefined,
          agentTrace: widgetType === 'x-sre-agent-trace' ? (data as unknown as AgentTraceData) : undefined,
          agentGraph: widgetType === 'x-sre-agent-graph' ? (data as unknown as AgentGraphData) : undefined,
          serviceTopology: widgetType === 'x-sre-service-topology' ? (data as unknown as ServiceTopologyData) : undefined,
        })
        get().addItem(item)
        set({ activeTab: dashType })
        return true
      }
    }
  },

  itemsOfType: (type) => get().items.filter((i) => i.type === type),

  typeCounts: () => {
    const counts: Record<DashboardDataType, number> = {
      traces: 0,
      logs: 0,
      metrics: 0,
      alerts: 0,
      council: 0,
      remediation: 0,
      analytics: 0,
    }
    for (const item of get().items) {
      counts[item.type] = (counts[item.type] || 0) + 1
    }
    return counts
  },

  hasData: () => get().items.length > 0,
}))
