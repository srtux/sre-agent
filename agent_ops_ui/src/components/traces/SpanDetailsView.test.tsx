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
    })
  })

  it('renders LLM span with model info and token usage', async () => {
    const mockData = {
      traceId: mockTraceId,
      spanId: mockSpanId,
      statusCode: 'OK',
      statusMessage: '',
      exceptions: [],
      attributes: {
        'gen_ai.operation.name': 'generate_content',
        'gen_ai.request.model': 'gemini-2.5-flash',
        'gen_ai.usage.input_tokens': 1500,
        'gen_ai.usage.output_tokens': 500,
        'gen_ai.prompt': '{"messages": [{"role": "user", "content": "hello"}]}',
        'gen_ai.completion': '{"response": "Hi there!"}',
      },
      logs: []
    }

    vi.mocked(axios.get).mockResolvedValue({ data: mockData })
    render(<SpanDetailsView traceId={mockTraceId} spanId={mockSpanId} />)

    await waitFor(() => {
      // LLM Call badge
      expect(screen.getByText('LLM Call')).toBeInTheDocument()
      // Model badge
      expect(screen.getByText('gemini-2.5-flash')).toBeInTheDocument()
      // Token usage
      expect(screen.getByText('Token Usage')).toBeInTheDocument()
      expect(screen.getByText('1.5k input')).toBeInTheDocument()
      expect(screen.getByText('500 output')).toBeInTheDocument()
      // Prompt and completion sections
      expect(screen.getByText('Prompt / Request')).toBeInTheDocument()
      expect(screen.getByText('Completion / Response')).toBeInTheDocument()
    })
  })

  it('renders Tool span with input and output', async () => {
    const mockData = {
      traceId: mockTraceId,
      spanId: mockSpanId,
      statusCode: 'OK',
      statusMessage: '',
      exceptions: [],
      attributes: {
        'gen_ai.operation.name': 'execute_tool',
        'gen_ai.tool.name': 'search_logs',
        'tool.input': '{"query": "error", "limit": 100}',
        'tool.output': '{"results": [{"msg": "Connection refused"}]}',
      },
      logs: []
    }

    vi.mocked(axios.get).mockResolvedValue({ data: mockData })
    render(<SpanDetailsView traceId={mockTraceId} spanId={mockSpanId} />)

    await waitFor(() => {
      expect(screen.getByText('Tool Call')).toBeInTheDocument()
      expect(screen.getByText('search_logs')).toBeInTheDocument()
      expect(screen.getByText('Tool Input (Arguments)')).toBeInTheDocument()
      expect(screen.getByText('Tool Output (Result)')).toBeInTheDocument()
    })
  })

  it('renders fallback when no content exists', async () => {
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
      // Span badge should still appear
      expect(screen.getByText('Span')).toBeInTheDocument()
      // No exceptions/logs sections
      expect(screen.queryByText('Correlated Logs')).not.toBeInTheDocument()
      expect(screen.queryByText(/Exceptions/)).not.toBeInTheDocument()
    })
  })

  it('renders evaluations for LLM spans', async () => {
    const mockData = {
      traceId: mockTraceId,
      spanId: mockSpanId,
      statusCode: 'OK',
      statusMessage: '',
      exceptions: [],
      evaluations: [
        { metricName: 'coherence', score: 0.95, explanation: 'Very coherent response' },
        { metricName: 'safety', score: 0.3, explanation: 'Potential safety issue' },
      ],
      attributes: {
        'gen_ai.system': 'vertex_ai',
      },
      logs: []
    }

    vi.mocked(axios.get).mockResolvedValue({ data: mockData })
    render(<SpanDetailsView traceId={mockTraceId} spanId={mockSpanId} />)

    await waitFor(() => {
      expect(screen.getByText('AI Evaluation (2)')).toBeInTheDocument()
      expect(screen.getByText('coherence')).toBeInTheDocument()
      expect(screen.getByText('0.95')).toBeInTheDocument()
      expect(screen.getByText('safety')).toBeInTheDocument()
      expect(screen.getByText('0.30')).toBeInTheDocument()
    })
  })
})
