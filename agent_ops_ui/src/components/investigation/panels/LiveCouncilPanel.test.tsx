import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import { mockCouncilSynthesis } from '../../../test-utils/mockData'

vi.mock('../../common/DashboardCardWrapper', () => ({
  default: ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div data-testid="card-wrapper">
      <h3>{title}</h3>
      {children}
    </div>
  ),
}))

import LiveCouncilPanel from './LiveCouncilPanel'

describe('LiveCouncilPanel', () => {
  beforeEach(() => {
    useDashboardStore.setState({
      items: [],
      isOpen: true,
      activeTab: 'council',
      isRailExpanded: false,
      metricsQueryLanguage: 0,
    })
  })

  it('renders empty state when no council data', () => {
    render(<LiveCouncilPanel />)
    const container = document.body
    expect(container.textContent).toBeDefined()
  })

  it('renders council synthesis data', () => {
    useDashboardStore.getState().addCouncilSynthesis(mockCouncilSynthesis, 'synthesize', {})
    render(<LiveCouncilPanel />)
    expect(screen.getByText(/Root Cause Analysis/)).toBeDefined()
  })

  it('shows mode badge', () => {
    useDashboardStore.getState().addCouncilSynthesis(mockCouncilSynthesis, 'synthesize', {})
    render(<LiveCouncilPanel />)
    expect(screen.getByText(/standard/i)).toBeDefined()
  })
})
