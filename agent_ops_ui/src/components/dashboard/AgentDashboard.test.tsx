import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AgentDashboard from './AgentDashboard'

// Mock child components to isolate the layout test
vi.mock('./DashboardToolbar', () => ({
  default: function MockToolbar() {
    return <div data-testid="dashboard-toolbar">Toolbar</div>
  },
}))

vi.mock('./panels/KpiGrid', () => ({
  default: function MockKpiGrid() {
    return <div data-testid="kpi-grid">KPI Grid</div>
  },
}))

vi.mock('./panels/InteractionMetricsPanel', () => ({
  default: function MockInteractionMetrics() {
    return <div data-testid="interaction-metrics">Interaction Metrics</div>
  },
}))

vi.mock('./panels/ModelAndToolPanel', () => ({
  default: function MockModelAndTool() {
    return <div data-testid="model-tool-panel">Model & Tool Panel</div>
  },
}))

vi.mock('./panels/AgentLogsPanel', () => ({
  default: function MockAgentLogs() {
    return <div data-testid="agent-logs-panel">Agent Logs</div>
  },
}))

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  )
}

describe('AgentDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the toolbar', () => {
    renderWithQuery(<AgentDashboard />)
    expect(screen.getByTestId('dashboard-toolbar')).toBeInTheDocument()
  })

  it('renders the KPI grid section', () => {
    renderWithQuery(<AgentDashboard />)
    expect(screen.getByTestId('kpi-grid')).toBeInTheDocument()
  })

  it('renders the interaction metrics section', () => {
    renderWithQuery(<AgentDashboard />)
    expect(screen.getByTestId('interaction-metrics')).toBeInTheDocument()
  })

  it('renders the model and tool panel section', () => {
    renderWithQuery(<AgentDashboard />)
    expect(screen.getByTestId('model-tool-panel')).toBeInTheDocument()
  })

  it('renders the agent logs section', () => {
    renderWithQuery(<AgentDashboard />)
    expect(screen.getByTestId('agent-logs-panel')).toBeInTheDocument()
  })

  it('renders all sections in correct order', () => {
    renderWithQuery(<AgentDashboard />)

    const toolbar = screen.getByTestId('dashboard-toolbar')
    const kpi = screen.getByTestId('kpi-grid')
    const metrics = screen.getByTestId('interaction-metrics')
    const modelTool = screen.getByTestId('model-tool-panel')
    const logs = screen.getByTestId('agent-logs-panel')

    // All sections should be present
    expect(toolbar).toBeInTheDocument()
    expect(kpi).toBeInTheDocument()
    expect(metrics).toBeInTheDocument()
    expect(modelTool).toBeInTheDocument()
    expect(logs).toBeInTheDocument()
  })
})
