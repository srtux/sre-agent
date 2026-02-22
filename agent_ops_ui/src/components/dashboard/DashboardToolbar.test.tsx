import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { DashboardFilterProvider } from '../../contexts/DashboardFilterContext'
import DashboardToolbar from './DashboardToolbar'

function renderWithProviders(
  ui: React.ReactElement,
  props?: { availableAgents?: string[]; loadingAgents?: boolean },
) {
  return render(
    <DashboardFilterProvider>
      {ui ?? <DashboardToolbar {...props} />}
    </DashboardFilterProvider>,
  )
}

describe('DashboardToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders time range selector with default value', () => {
    renderWithProviders(<DashboardToolbar />)
    const select = screen.getByDisplayValue('Last 24 hours')
    expect(select).toBeInTheDocument()
  })

  it('renders all time range options', () => {
    renderWithProviders(<DashboardToolbar />)
    expect(screen.getByText('Last 1 hour')).toBeInTheDocument()
    expect(screen.getByText('Last 6 hours')).toBeInTheDocument()
    expect(screen.getByText('Last 24 hours')).toBeInTheDocument()
    expect(screen.getByText('Last 7 days')).toBeInTheDocument()
    expect(screen.getByText('Last 30 days')).toBeInTheDocument()
  })

  it('renders agent multi-select showing "All Agents" by default', () => {
    renderWithProviders(<DashboardToolbar availableAgents={['agent-a', 'agent-b']} />)
    expect(screen.getByText('All Agents')).toBeInTheDocument()
  })

  it('renders group by agent toggle', () => {
    renderWithProviders(<DashboardToolbar />)
    const toggle = screen.getByRole('button', { name: 'Group by agent' })
    expect(toggle).toBeInTheDocument()
    expect(toggle).toHaveAttribute('aria-pressed', 'false')
  })

  it('toggles group by agent on click', () => {
    renderWithProviders(<DashboardToolbar />)
    const toggle = screen.getByRole('button', { name: 'Group by agent' })

    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-pressed', 'false')
  })

  it('changes time range on select change', () => {
    renderWithProviders(<DashboardToolbar />)
    const select = screen.getByDisplayValue('Last 24 hours') as HTMLSelectElement

    fireEvent.change(select, { target: { value: '7d' } })
    expect(select.value).toBe('7d')
  })

  it('renders reset button', () => {
    renderWithProviders(<DashboardToolbar />)
    expect(screen.getByText('Reset')).toBeInTheDocument()
  })

  it('shows loading state for agents', () => {
    renderWithProviders(<DashboardToolbar availableAgents={[]} loadingAgents={true} />)
    // Open the dropdown
    fireEvent.click(screen.getByText('All Agents'))
    expect(screen.getByText('Loading agents...')).toBeInTheDocument()
  })

  it('shows empty state when no agents available', () => {
    renderWithProviders(<DashboardToolbar availableAgents={[]} loadingAgents={false} />)
    fireEvent.click(screen.getByText('All Agents'))
    expect(screen.getByText('No agents found')).toBeInTheDocument()
  })

  it('shows available agents in dropdown', () => {
    renderWithProviders(
      <DashboardToolbar availableAgents={['trace-analyst', 'log-analyst']} />,
    )
    fireEvent.click(screen.getByText('All Agents'))
    expect(screen.getByText('trace-analyst')).toBeInTheDocument()
    expect(screen.getByText('log-analyst')).toBeInTheDocument()
  })
})
