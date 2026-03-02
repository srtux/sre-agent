import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AgentGraph from './AgentGraph'
import { mockAgentGraph } from '../../test-utils/mockData'

describe('AgentGraph', () => {
  it('renders node labels', () => {
    render(<AgentGraph data={mockAgentGraph} />)
    expect(screen.getByText('sre-agent')).toBeDefined()
    expect(screen.getByText('trace-analyst')).toBeDefined()
    expect(screen.getByText('log-analyst')).toBeDefined()
  })

  it('renders execution counts', () => {
    render(<AgentGraph data={mockAgentGraph} />)
    expect(screen.getByText(/100/)).toBeDefined()
    expect(screen.getByText(/80/)).toBeDefined()
  })

  it('renders edge connections', () => {
    const { container } = render(<AgentGraph data={mockAgentGraph} />)
    // Visual connections should exist
    expect(container.querySelectorAll('[style]').length).toBeGreaterThan(0)
  })
})
