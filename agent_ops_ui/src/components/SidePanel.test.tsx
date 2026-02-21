import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import SidePanel from './SidePanel'

const mockNodeDetail = {
  nodeId: 'agent-1',
  label: 'Test Agent',
  nodeType: 'agent',
  totalInvocations: 100,
  errorCount: 5,
  errorRate: 5.0,
  latency: {
    min: 10,
    max: 100,
    avg: 50,
    p50: 45,
    p95: 90,
    p99: 99
  },
  inputTokens: 1000,
  outputTokens: 2000,
  estimatedCost: 0.05,
  topErrors: [
    { message: 'Failed to connect', count: 5 }
  ],
  recentPayloads: []
}

const mockToolDetail = {
  ...mockNodeDetail,
  nodeId: 'tool-1',
  label: 'Test Tool',
  nodeType: 'tool',
}

vi.mock('axios')

describe('SidePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders View Traces button for agent nodes', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({ data: mockNodeDetail })
    render(
      <SidePanel
        selected={{ kind: 'node', id: 'agent-1' }}
        projectId="test-project"
        hours={24}
        onClose={vi.fn()}
        sparklineData={null}
      />
    )

    // Wait for the View Traces button to appear
    expect(await screen.findByText('View Traces')).toBeInTheDocument()
    expect(screen.getByText('Test Agent')).toBeInTheDocument()

    // Check that top errors are shown
    expect(screen.getByText('Failed to connect')).toBeInTheDocument()
  })

  it('does not render View Traces button for tool nodes', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({ data: mockToolDetail })
    render(
      <SidePanel
        selected={{ kind: 'node', id: 'tool-1' }}
        projectId="test-project"
        hours={24}
        onClose={vi.fn()}
        sparklineData={null}
      />
    )

    // Wait for render
    expect(await screen.findByText('Test Tool')).toBeInTheDocument()

    // View traces should not exist
    expect(screen.queryByText('View Traces')).not.toBeInTheDocument()
  })
})
