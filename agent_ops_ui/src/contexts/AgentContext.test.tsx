import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { AgentProvider, useAgentContext } from './AgentContext'

vi.mock('axios')

const mockAgents = {
  agents: [
    { serviceName: 'agent-A', totalSessions: 10 },
    { serviceName: 'agent-B', totalSessions: 100 },
    { serviceName: 'agent-C', totalSessions: 50 },
  ]
}

function TestConsumer() {
  const { serviceName, availableAgents, loadingAgents } = useAgentContext()
  return (
    <div>
      <span data-testid="serviceName">{serviceName}</span>
      <span data-testid="loading">{loadingAgents.toString()}</span>
      <span data-testid="count">{availableAgents.length}</span>
    </div>
  )
}

describe('AgentContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('fetches agents and auto-selects the highest volume agent', async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: mockAgents })

    render(
      <AgentProvider projectId="test-project">
        <TestConsumer />
      </AgentProvider>
    )

    // Should initially be empty and loading
    expect(screen.getByTestId('loading').textContent).toBe('true')

    // Wait for fetch to complete
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false')
    })

    // Should have auto-selected agent-B since it has 100 total sessions
    expect(screen.getByTestId('serviceName').textContent).toBe('agent-B')
    expect(screen.getByTestId('count').textContent).toBe('3')

    // Should have saved to localStorage
    expect(localStorage.getItem('agent_graph_service_name')).toBe('agent-B')
  })

  it('keeps existing selected agent if it exists in fetched agents', async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: mockAgents })
    localStorage.setItem('agent_graph_service_name', 'agent-C')

    render(
      <AgentProvider projectId="test-project">
        <TestConsumer />
      </AgentProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false')
    })

    // Should keep agent-C
    expect(screen.getByTestId('serviceName').textContent).toBe('agent-C')
  })
})
