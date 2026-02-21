import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import GraphToolbar from './GraphToolbar'

const mockFilters = {
  projectId: 'test-project',
  hours: 24,
  errorsOnly: false,
  traceDataset: 'traces',
  serviceName: 'agent-A',
}

const mockOnChange = vi.fn()
const mockOnLoad = vi.fn()
const mockOnAutoRefreshChange = vi.fn()

vi.mock('../contexts/AgentContext', () => ({
  useAgentContext: vi.fn(),
}))
import { useAgentContext } from '../contexts/AgentContext'

const mockAgentContextValue = {
  serviceName: 'agent-A',
  setServiceName: vi.fn(),
  availableAgents: [
    { serviceName: 'agent-A', agentId: 'a', agentName: 'A', totalSessions: 10, firstSeen: '1', lastSeen: '1', tools: [], totalTurns: 0, inputTokens: 0, outputTokens: 0, errorCount: 0, errorRate: 0, p50DurationMs: 0, p95DurationMs: 0 },
    { serviceName: 'agent-B', agentId: 'b', agentName: 'B', totalSessions: 20, firstSeen: '1', lastSeen: '1', tools: [], totalTurns: 0, inputTokens: 0, outputTokens: 0, errorCount: 0, errorRate: 0, p50DurationMs: 0, p95DurationMs: 0 }
  ],
  loadingAgents: false,
  errorAgents: null,
}

describe('GraphToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAgentContext).mockReturnValue(mockAgentContextValue)
  })

  it('renders Agent Selector and Time Range', () => {
    render(
      <GraphToolbar
        filters={mockFilters}
        onChange={mockOnChange}
        onLoad={mockOnLoad}
        loading={false}
        autoRefresh={{ enabled: false, intervalSeconds: 60 }}
        onAutoRefreshChange={mockOnAutoRefreshChange}
        lastUpdated={null}
      />
    )

    // Check if dropdown has the agents
    const select = screen.getByRole('combobox') as HTMLSelectElement
    expect(select.value).toBe('agent-A')
    expect(screen.getByText('agent-A')).toBeInTheDocument()
    expect(screen.getByText('agent-B')).toBeInTheDocument()
  })

  it('calls setServiceName when agent is changed', () => {
    render(
      <GraphToolbar
        filters={mockFilters}
        onChange={mockOnChange}
        onLoad={mockOnLoad}
        loading={false}
        autoRefresh={{ enabled: false, intervalSeconds: 60 }}
        onAutoRefreshChange={mockOnAutoRefreshChange}
        lastUpdated={null}
      />
    )

    const select = screen.getByRole('combobox') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'agent-B' } })
    expect(mockAgentContextValue.setServiceName).toHaveBeenCalledWith('agent-B')
  })

  it('disables load button when no project ID or loading', () => {
    const { rerender } = render(
      <GraphToolbar
        filters={{ ...mockFilters, projectId: '' }}
        onChange={mockOnChange}
        onLoad={mockOnLoad}
        loading={false}
        autoRefresh={{ enabled: false, intervalSeconds: 60 }}
        onAutoRefreshChange={mockOnAutoRefreshChange}
        lastUpdated={null}
      />
    )

    expect(screen.getByText('Load')).toHaveProperty('disabled', true)

    rerender(
      <GraphToolbar
        filters={mockFilters}
        onChange={mockOnChange}
        onLoad={mockOnLoad}
        loading={true}
        autoRefresh={{ enabled: false, intervalSeconds: 60 }}
        onAutoRefreshChange={mockOnAutoRefreshChange}
        lastUpdated={null}
      />
    )

    expect(screen.getByText('Loading...')).toHaveProperty('disabled', true)
  })
})
