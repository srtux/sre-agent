import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import LogEntriesViewer from './LogEntriesViewer'
import { mockLogEntriesData } from '../../test-utils/mockData'

vi.mock('../common/JsonPayloadViewer', () => ({
  default: ({ data }: { data: unknown }) => <pre data-testid="json">{JSON.stringify(data)}</pre>,
}))

describe('LogEntriesViewer', () => {
  it('renders log entries', () => {
    render(<LogEntriesViewer data={mockLogEntriesData} />)
    expect(screen.getByText(/Connection refused/)).toBeDefined()
  })

  it('shows severity labels', () => {
    render(<LogEntriesViewer data={mockLogEntriesData} />)
    // Severity text appears both in filter chip buttons and in entry badges.
    // Use getAllByText since there are multiple elements with the same text.
    expect(screen.getAllByText('ERROR').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('WARNING').length).toBeGreaterThanOrEqual(1)
  })

  it('renders filter chips', () => {
    render(<LogEntriesViewer data={mockLogEntriesData} />)
    // The component renders filter buttons: ALL, ERROR, WARNING, INFO, DEBUG
    expect(screen.getByText('ALL')).toBeDefined()
    expect(screen.getByText('DEBUG')).toBeDefined()
  })
})
