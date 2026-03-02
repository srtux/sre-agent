import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AgentActivityGraph from './AgentActivityGraph'
import { mockAgentActivity } from '../../test-utils/mockData'

describe('AgentActivityGraph', () => {
  it('renders agent nodes', () => {
    render(<AgentActivityGraph data={mockAgentActivity} />)
    expect(screen.getByText('Coordinator')).toBeDefined()
    expect(screen.getByText('Trace Analyst')).toBeDefined()
    expect(screen.getByText('Log Analyst')).toBeDefined()
  })

  it('renders data source nodes', () => {
    render(<AgentActivityGraph data={mockAgentActivity} />)
    expect(screen.getByText('Cloud Trace')).toBeDefined()
    expect(screen.getByText('Cloud Logging')).toBeDefined()
  })

  it('shows current phase', () => {
    render(<AgentActivityGraph data={mockAgentActivity} />)
    expect(screen.getByText(/Analyzing logs/)).toBeDefined()
  })
})
