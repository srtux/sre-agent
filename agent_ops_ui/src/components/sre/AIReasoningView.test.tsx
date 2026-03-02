import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import AIReasoningView from './AIReasoningView'

describe('AIReasoningView', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // The component expects { steps: Array<{title, content}>, conclusion: string }
  const mockData = {
    steps: [
      { title: 'Trace Analysis', content: 'Analyzed 42 traces with elevated latency' },
      { title: 'Correlation', content: 'Correlated with deployment event at 09:50' },
      { title: 'Root Cause', content: 'Identified connection pool exhaustion pattern' },
    ],
    conclusion: 'Based on trace analysis, the root cause is a connection pool leak.',
  }

  it('renders reasoning text', () => {
    render(<AIReasoningView data={mockData} />)
    // Advance timers inside act() so React processes state updates properly
    // 3 steps, each revealed 200ms apart, plus one more to trigger the conclusion
    act(() => { vi.advanceTimersByTime(200) }) // revealedCount -> 1
    act(() => { vi.advanceTimersByTime(200) }) // revealedCount -> 2
    act(() => { vi.advanceTimersByTime(200) }) // revealedCount -> 3 (all steps revealed, conclusion appears)
    expect(screen.getByText(/connection pool leak/)).toBeDefined()
  })

  it('renders reasoning steps', () => {
    render(<AIReasoningView data={mockData} />)
    // Steps are rendered immediately but with opacity=0 until revealed.
    // The text is still in the DOM though, just invisible.
    expect(screen.getByText(/42 traces/)).toBeDefined()
    expect(screen.getByText(/deployment event/)).toBeDefined()
  })
})
