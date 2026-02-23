import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import SpanDetailsView from './SpanDetailsView'
import { useAgentContext } from '../../contexts/AgentContext'

vi.mock('axios')
vi.mock('../../contexts/AgentContext', () => ({
  useAgentContext: vi.fn(),
}))

describe('SpanDetailsView', () => {
  const mockTraceId = '8f4de13a30f76906a206f477cc6777a4' // pragma: allowlist secret
  const mockSpanId = '74e87600bb9ffefc' // pragma: allowlist secret

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAgentContext).mockReturnValue({
      projectId: 'test-project',
      serviceName: '',
      setServiceName: vi.fn(),
      availableAgents: [],
      loadingAgents: false,
      errorAgents: null,
      registryViewMode: 'card',
      setRegistryViewMode: vi.fn(),
    })
  })

  it('renders loading state initially', () => {
    vi.mocked(axios.get).mockReturnValue(new Promise(() => { }))
    render(<SpanDetailsView traceId={mockTraceId} spanId={mockSpanId} />)
    expect(screen.getByText('Loading span details...')).toBeInTheDocument()
  })

  it('renders error state on failure', async () => {
    vi.mocked(axios.get).mockRejectedValue({
      response: { data: { detail: 'Server error' } },
    })
    render(<SpanDetailsView traceId={mockTraceId} spanId={mockSpanId} />)

    await waitFor(() => {
      expect(screen.getByText(/Failed to load span details: Server error/)).toBeInTheDocument()
    })
  })

  it('renders span details including logs and exceptions', async () => {
    const mockData = {
      traceId: mockTraceId,
      spanId: mockSpanId,
      statusCode: 'ERROR',
      statusMessage: 'Spock is dead',
      exceptions: [
        {
          type: 'DeathException',
          message: 'He is dead, Jim',
          stacktrace: 'at Transporter.beam(...)'
        }
      ],
      attributes: {
        'ship.name': 'Enterprise',
        'captain': 'Kirk'
      },
      logs: [
        {
          timestamp: '2026-02-22T12:00:00Z',
          severity: 'ERROR',
          payload: 'Warp core breach'
        },
        {
          timestamp: '2026-02-22T12:00:01Z',
          severity: 'INFO',
          payload: { message: 'Attempting containment', logic: 'failed' }
        }
      ]
    }

    vi.mocked(axios.get).mockResolvedValue({ data: mockData })
    render(<SpanDetailsView traceId={mockTraceId} spanId={mockSpanId} />)

    // Wait for content
    await waitFor(() => {
      expect(screen.getByText(/DeathException/)).toBeInTheDocument()
      expect(screen.getByText(/He is dead, Jim/)).toBeInTheDocument()
      expect(screen.getByText(/Warp core breach/)).toBeInTheDocument()
      expect(screen.getByText(/Attempting containment/)).toBeInTheDocument()
      expect(screen.getByText(/"ship.name": "Enterprise"/)).toBeInTheDocument()
    })
  })

  it('renders fallback when no metrics/logs exist', async () => {
    const mockData = {
      traceId: mockTraceId,
      spanId: mockSpanId,
      statusCode: 'OK',
      statusMessage: '',
      exceptions: [],
      attributes: {},
      logs: []
    }

    vi.mocked(axios.get).mockResolvedValue({ data: mockData })
    render(<SpanDetailsView traceId={mockTraceId} spanId={mockSpanId} />)

    await waitFor(() => {
      expect(screen.getByText('No attributes collected.')).toBeInTheDocument()
      expect(screen.queryByText('Correlated Logs')).not.toBeInTheDocument()
      expect(screen.queryByText('Exceptions')).not.toBeInTheDocument()
    })
  })
})
