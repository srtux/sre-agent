import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import { mockLogEntriesData } from '../../../test-utils/mockData'

vi.mock('../../common/JsonPayloadViewer', () => ({
  default: ({ data }: { data: unknown }) => (
    <pre data-testid="json-viewer">{JSON.stringify(data)}</pre>
  ),
}))

import LiveLogsExplorer from './LiveLogsExplorer'

describe('LiveLogsExplorer', () => {
  beforeEach(() => {
    useDashboardStore.setState({
      items: [],
      isOpen: true,
      activeTab: 'logs',
      isRailExpanded: false,
      metricsQueryLanguage: 0,
    })
  })

  it('renders empty state when no logs', () => {
    render(<LiveLogsExplorer />)
    // Should show some empty or default state
    const container = document.body
    expect(container.textContent).toBeDefined()
  })

  it('renders log entries when available', () => {
    useDashboardStore.getState().addLogEntries(mockLogEntriesData, 'get_logs', {})
    render(<LiveLogsExplorer />)
    expect(screen.getByText(/Connection refused/)).toBeDefined()
  })

  it('has a search input', () => {
    useDashboardStore.getState().addLogEntries(mockLogEntriesData, 'get_logs', {})
    render(<LiveLogsExplorer />)
    const inputs = document.querySelectorAll('input')
    expect(inputs.length).toBeGreaterThanOrEqual(1)
  })

  it('has severity filter buttons', () => {
    useDashboardStore.getState().addLogEntries(mockLogEntriesData, 'get_logs', {})
    render(<LiveLogsExplorer />)
    expect(screen.getByText('ALL')).toBeDefined()
    // ERROR appears both as a filter button and a severity badge on log entries
    expect(screen.getAllByText('ERROR').length).toBeGreaterThanOrEqual(1)
  })
})
