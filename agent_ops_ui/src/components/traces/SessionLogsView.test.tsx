import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
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
    expect(screen.getByText(/Select a session to view its trajectory logs/i)).toBeInTheDocument()
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
    expect(screen.getByText(/No trajectory data found for this session/i)).toBeInTheDocument()
  })

  it('renders trajectory events correctly', () => {
    vi.mocked(useSessionTrajectoryModule.useSessionTrajectory).mockReturnValue({
      data: {
        sessionId: 'test',
        trajectory: [
          {
            traceId: 'tr1',
            spanId: 'sp1',
            startTime: '2026-02-27T12:00:00Z',
            nodeType: 'LLM',
            nodeLabel: 'generate_content',
            durationMs: 1500,
            statusCode: 0,
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

    // Check basic rendering elements
    expect(screen.getByText('generate_content')).toBeInTheDocument()
    expect(screen.getByText('1500 ms')).toBeInTheDocument()
    expect(screen.getByText('Input / Prompt')).toBeInTheDocument()
    expect(screen.getByText('Output / Completion')).toBeInTheDocument()
    expect(screen.getByText(/Some DB query/i)).toBeInTheDocument()
    expect(screen.getByText(/coherence: 0.90/i)).toBeInTheDocument()
  })
})
