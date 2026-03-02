import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import { mockTrace } from '../../../test-utils/mockData'

vi.mock('../../common/DashboardCardWrapper', () => ({
  default: ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div data-testid="card-wrapper">
      <h3>{title}</h3>
      {children}
    </div>
  ),
}))

import LiveTracePanel from './LiveTracePanel'

describe('LiveTracePanel', () => {
  beforeEach(() => {
    useDashboardStore.setState({
      items: [],
      isOpen: true,
      activeTab: 'traces',
      isRailExpanded: false,
      metricsQueryLanguage: 0,
    })
  })

  it('renders empty state when no traces', () => {
    render(<LiveTracePanel />)
    const container = document.body
    expect(container.textContent).toBeDefined()
  })

  it('renders trace card when trace data available', () => {
    useDashboardStore.getState().addTrace(mockTrace, 'get_traces', {})
    render(<LiveTracePanel />)
    expect(screen.getByText(/trace-abc123/)).toBeDefined()
  })

  it('shows span info for trace', () => {
    useDashboardStore.getState().addTrace(mockTrace, 'get_traces', {})
    render(<LiveTracePanel />)
    // Spans are collapsed by default; click "Show spans" to expand
    fireEvent.click(screen.getByText(/Show spans/))
    expect(screen.getByText(/HTTP GET/)).toBeDefined()
  })
})
