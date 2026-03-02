import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useDashboardStore } from '../../stores/dashboardStore'

// Mock all live panels
vi.mock('./panels/LiveTracePanel', () => ({ default: () => <div data-testid="live-traces">Traces</div> }))
vi.mock('./panels/LiveLogsExplorer', () => ({ default: () => <div data-testid="live-logs">Logs</div> }))
vi.mock('./panels/LiveMetricsPanel', () => ({ default: () => <div data-testid="live-metrics">Metrics</div> }))
vi.mock('./panels/LiveAlertsPanel', () => ({ default: () => <div data-testid="live-alerts">Alerts</div> }))
vi.mock('./panels/LiveCouncilPanel', () => ({ default: () => <div data-testid="live-council">Council</div> }))
vi.mock('./panels/LiveRemediationPanel', () => ({ default: () => <div data-testid="live-remediation">Remediation</div> }))
vi.mock('./panels/LiveChartsPanel', () => ({ default: () => <div data-testid="live-charts">Charts</div> }))

import DashboardPanel from './DashboardPanel'

describe('DashboardPanel', () => {
  beforeEach(() => {
    useDashboardStore.setState({
      items: [],
      isOpen: true,
      activeTab: 'traces',
      isRailExpanded: false,
      metricsQueryLanguage: 0,
    })
  })

  it('renders tab bar with all category labels', () => {
    render(<DashboardPanel />)
    expect(screen.getByText('Traces')).toBeDefined()
    expect(screen.getByText('Logs')).toBeDefined()
    expect(screen.getByText('Metrics')).toBeDefined()
    expect(screen.getByText('Alerts')).toBeDefined()
    expect(screen.getByText('Council')).toBeDefined()
  })

  it('renders active panel content', () => {
    useDashboardStore.getState().addTrace({ traceId: 't1', spans: [] }, 'test', {})
    useDashboardStore.setState({ activeTab: 'traces' })
    render(<DashboardPanel />)
    expect(screen.getByTestId('live-traces')).toBeDefined()
  })

  it('switching tab changes displayed panel', () => {
    render(<DashboardPanel />)
    fireEvent.click(screen.getByText('Logs'))
    expect(useDashboardStore.getState().activeTab).toBe('logs')
  })

  it('shows count badges when items exist', () => {
    useDashboardStore.getState().addTrace({ traceId: 't1', spans: [] }, 'test', {})
    useDashboardStore.getState().addTrace({ traceId: 't2', spans: [] }, 'test', {})
    render(<DashboardPanel />)
    // Badge showing count 2 should appear
    expect(screen.getByText('2')).toBeDefined()
  })
})
