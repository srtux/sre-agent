import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SessionLogsView } from './SessionLogsView'
import * as useSessionTrajectoryModule from '../../hooks/useSessionTrajectory'

// Mock the hook
vi.mock('../../hooks/useSessionTrajectory', () => ({
  useSessionTrajectory: vi.fn()
}))

describe('SessionLogsView', () => {
  it('renders instructions when no session is selected', () => {
    vi.mocked(useSessionTrajectoryModule.useSessionTrajectory).mockReturnValue({
      data: null,
      loading: false,
      error: null
    })

    render(<SessionLogsView sessionId={null} activeTab="traces" viewMode="log" />)
    expect(screen.getByText(/Select a session to view its execution trace/i)).toBeInTheDocument()
  })

  it('renders loading state', () => {
    vi.mocked(useSessionTrajectoryModule.useSessionTrajectory).mockReturnValue({
      data: null,
      loading: true,
      error: null
    })

    const { container } = render(<SessionLogsView sessionId="test-session" activeTab="traces" viewMode="log" />)
    expect(container.querySelector('div[style*="border-radius: 50%"]')).toBeInTheDocument()
  })

  it('renders empty message when no trajectory is returned', () => {
    vi.mocked(useSessionTrajectoryModule.useSessionTrajectory).mockReturnValue({
      data: { sessionId: 'test', trajectory: [] },
      loading: false,
      error: null
    })

    render(<SessionLogsView sessionId="test-session" activeTab="traces" viewMode="log" />)
    expect(screen.getByText(/No trace data found for this session/i)).toBeInTheDocument()
  })

  it('renders trajectory events in waterfall layout', () => {
    vi.mocked(useSessionTrajectoryModule.useSessionTrajectory).mockReturnValue({
      data: {
        sessionId: 'test',
        trajectory: [
          {
            traceId: 'tr1',
            spanId: 'sp1',
            parentSpanId: null,
            startTime: '2026-02-27T12:00:00Z',
            nodeType: 'LLM',
            nodeLabel: 'generate_content',
            durationMs: 1500,
            statusCode: 0,
            statusMessage: null,
            inputTokens: 500,
            outputTokens: 200,
            totalTokens: 700,
            model: 'gemini-2.5-flash',
            prompt: '{"query": "hello"}',
            completion: '{"reply": "hi"}',
            systemMessage: null,
            toolInput: null,
            toolOutput: null,
            evaluations: [{ metricName: 'coherence', score: 0.9, explanation: 'good' }],
            logs: [{ timestamp: '2026-02-27T12:00:00Z', severity: 'INFO', payload: 'Some DB query' }]
          }
        ]
      },
      loading: false,
      error: null
    })

    render(<SessionLogsView sessionId="test-session" activeTab="traces" viewMode="log" />)

    // Check waterfall header stats
    expect(screen.getByText('Session Trace')).toBeInTheDocument()
    expect(screen.getByText('1 spans')).toBeInTheDocument()

    // Check node label in waterfall
    expect(screen.getByText('generate_content')).toBeInTheDocument()

    // Check model badge
    expect(screen.getByText('gemini-2.5-flash')).toBeInTheDocument()

    // Check summary stats
    expect(screen.getByText('LLM')).toBeInTheDocument()
  })

  it('shows detail panel when a span row is clicked', () => {
    vi.mocked(useSessionTrajectoryModule.useSessionTrajectory).mockReturnValue({
      data: {
        sessionId: 'test',
        trajectory: [
          {
            traceId: 'tr1',
            spanId: 'sp1',
            parentSpanId: null,
            startTime: '2026-02-27T12:00:00Z',
            nodeType: 'Tool',
            nodeLabel: 'search_logs',
            durationMs: 800,
            statusCode: 0,
            statusMessage: null,
            inputTokens: 0,
            outputTokens: 0,
            totalTokens: 0,
            model: null,
            prompt: null,
            completion: null,
            systemMessage: null,
            toolInput: '{"query": "error logs"}',
            toolOutput: '{"results": ["log1", "log2"]}',
            evaluations: [],
            logs: []
          }
        ]
      },
      loading: false,
      error: null
    })

    render(<SessionLogsView sessionId="test-session" activeTab="traces" viewMode="log" />)

    // Click the span row to expand detail panel
    fireEvent.click(screen.getByText('search_logs'))

    // Check detail panel content
    expect(screen.getByText('Tool Input (Arguments)')).toBeInTheDocument()
    expect(screen.getByText('Tool Output (Result)')).toBeInTheDocument()
  })

  it('renders tree hierarchy with parent-child spans', () => {
    vi.mocked(useSessionTrajectoryModule.useSessionTrajectory).mockReturnValue({
      data: {
        sessionId: 'test',
        trajectory: [
          {
            traceId: 'tr1',
            spanId: 'sp-root',
            parentSpanId: null,
            startTime: '2026-02-27T12:00:00Z',
            nodeType: 'Agent',
            nodeLabel: 'root_agent',
            durationMs: 5000,
            statusCode: 0,
            statusMessage: null,
            inputTokens: 0,
            outputTokens: 0,
            totalTokens: 0,
            model: null,
            prompt: null,
            completion: null,
            systemMessage: null,
            toolInput: null,
            toolOutput: null,
            evaluations: [],
            logs: []
          },
          {
            traceId: 'tr1',
            spanId: 'sp-child',
            parentSpanId: 'sp-root',
            startTime: '2026-02-27T12:00:01Z',
            nodeType: 'LLM',
            nodeLabel: 'generate_content',
            durationMs: 2000,
            statusCode: 0,
            statusMessage: null,
            inputTokens: 1000,
            outputTokens: 500,
            totalTokens: 1500,
            model: 'gemini-2.5-flash',
            prompt: null,
            completion: null,
            systemMessage: null,
            toolInput: null,
            toolOutput: null,
            evaluations: [],
            logs: []
          }
        ]
      },
      loading: false,
      error: null
    })

    render(<SessionLogsView sessionId="test-session" activeTab="traces" viewMode="log" />)

    // Both spans should be visible
    expect(screen.getByText('root_agent')).toBeInTheDocument()
    expect(screen.getByText('generate_content')).toBeInTheDocument()

    // Summary should show 2 spans
    expect(screen.getByText('2 spans')).toBeInTheDocument()
  })

  it('shows error indicator for failed spans', () => {
    vi.mocked(useSessionTrajectoryModule.useSessionTrajectory).mockReturnValue({
      data: {
        sessionId: 'test',
        trajectory: [
          {
            traceId: 'tr1',
            spanId: 'sp1',
            parentSpanId: null,
            startTime: '2026-02-27T12:00:00Z',
            nodeType: 'Tool',
            nodeLabel: 'failing_tool',
            durationMs: 100,
            statusCode: 2,
            statusMessage: 'Connection timeout',
            inputTokens: 0,
            outputTokens: 0,
            totalTokens: 0,
            model: null,
            prompt: null,
            completion: null,
            systemMessage: null,
            toolInput: null,
            toolOutput: null,
            evaluations: [],
            logs: []
          }
        ]
      },
      loading: false,
      error: null
    })

    render(<SessionLogsView sessionId="test-session" activeTab="traces" viewMode="log" />)

    // Error badge should be visible
    expect(screen.getByText('ERR')).toBeInTheDocument()

    // Error count in header
    expect(screen.getByText('errors')).toBeInTheDocument()
  })
})
