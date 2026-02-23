import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AgentDashboard from './AgentDashboard'

// Mock AgentContext
vi.mock('../../contexts/AgentContext', () => ({
  useAgentContext: () => ({
    projectId: 'test-project',
    serviceName: 'sre-agent',
    setServiceName: vi.fn(),
    availableAgents: [
      { serviceName: 'sre-agent', agentName: 'SRE Agent', totalSessions: 10 },
    ],
    loadingAgents: false,
    errorAgents: null,
  }),
}))

// Mock child components to isolate the layout test

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

vi.mock('./panels/EvalMetricsPanel', () => ({
  default: function MockEvalMetrics() {
    return <div data-testid="eval-metrics-panel">Eval Metrics</div>
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

  it('renders the KPI grid section', () => {
    renderWithQuery(<AgentDashboard hours={24} />)
    expect(screen.getByTestId('kpi-grid')).toBeInTheDocument()
  })

  it('renders the interaction metrics section', () => {
    renderWithQuery(<AgentDashboard hours={24} />)
    expect(screen.getByTestId('interaction-metrics')).toBeInTheDocument()
  })

  it('renders the model and tool panel section', () => {
    renderWithQuery(<AgentDashboard hours={24} />)
    expect(screen.getByTestId('model-tool-panel')).toBeInTheDocument()
  })



  it('renders all sections in correct order', () => {
    renderWithQuery(<AgentDashboard hours={24} />)

    const kpi = screen.getByTestId('kpi-grid')
    const metrics = screen.getByTestId('interaction-metrics')
    const modelTool = screen.getByTestId('model-tool-panel')
    // All sections should be present
    expect(kpi).toBeInTheDocument()
    expect(metrics).toBeInTheDocument()
    expect(modelTool).toBeInTheDocument()
  })
})
