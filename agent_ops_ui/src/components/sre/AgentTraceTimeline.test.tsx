import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AgentTraceTimeline from './AgentTraceTimeline'
import { mockAgentTrace } from '../../test-utils/mockData'

describe('AgentTraceTimeline', () => {
  it('renders root agent name', () => {
    render(<AgentTraceTimeline data={mockAgentTrace} />)
    // Root agent name is rendered in the summary header as a <span>.
    // D3 may also render "sre-agent" in SVG text, so use getAllByText.
    const matches = screen.getAllByText(/sre-agent/)
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  it('renders summary stats', () => {
    render(<AgentTraceTimeline data={mockAgentTrace} />)
    // The summary header span contains duration, LLM calls, tool calls, and total tokens.
    // Use getAllByText since D3 also renders "5.0s" in SVG axis/bar labels.
    const matches = screen.getAllByText(/5\.0s/)
    expect(matches.length).toBeGreaterThanOrEqual(1)
    // Verify the summary span also contains the call counts
    const summarySpan = matches.find(el => el.textContent?.includes('LLM calls'))
    expect(summarySpan).toBeDefined()
    expect(summarySpan!.textContent).toContain('1 LLM calls')
    expect(summarySpan!.textContent).toContain('1 tool calls')
  })

  it('shows total duration', () => {
    render(<AgentTraceTimeline data={mockAgentTrace} />)
    // 5000ms formatted as "5.0s" — appears in multiple places
    const matches = screen.getAllByText(/5\.0s/)
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  it('renders legend', () => {
    render(<AgentTraceTimeline data={mockAgentTrace} />)
    // The legend shows kind names with underscores replaced by spaces
    expect(screen.getByText('agent invocation')).toBeDefined()
    expect(screen.getByText('tool execution')).toBeDefined()
  })
})
