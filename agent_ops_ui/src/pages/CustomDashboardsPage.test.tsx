import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CustomDashboardsPage from './CustomDashboardsPage'

const mockDashboards = [
  { id: 'd1', name: 'SLO Overview', description: 'SLO burn rates', widgetCount: 4, lastModified: '2026-02-28T12:00:00Z' },
  { id: 'd2', name: 'Trace Health', description: '', widgetCount: 2, lastModified: '2026-02-27T10:00:00Z' },
]

const mockCreateMutate = vi.fn()
const mockDeleteMutate = vi.fn()

vi.mock('../hooks/useCustomDashboards', () => ({
  useCustomDashboards: () => ({ data: mockDashboards, isLoading: false, error: null }),
  useCreateDashboard: () => ({ mutate: mockCreateMutate, isPending: false }),
  useDeleteDashboard: () => ({ mutate: mockDeleteMutate, isPending: false }),
}))

vi.mock('../components/common/ShimmerLoading', () => ({
  default: () => <div data-testid="shimmer">Loading...</div>,
}))

vi.mock('../components/common/ErrorBanner', () => ({
  default: ({ message }: { message: string }) => <div data-testid="error-banner">{message}</div>,
}))

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('CustomDashboardsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page title', () => {
    render(<CustomDashboardsPage />, { wrapper })
    expect(screen.getByText('Custom Dashboards')).toBeDefined()
  })

  it('renders dashboard cards', () => {
    render(<CustomDashboardsPage />, { wrapper })
    expect(screen.getByText('SLO Overview')).toBeDefined()
    expect(screen.getByText('Trace Health')).toBeDefined()
  })

  it('renders widget counts', () => {
    render(<CustomDashboardsPage />, { wrapper })
    expect(screen.getByText('4 widgets')).toBeDefined()
    expect(screen.getByText('2 widgets')).toBeDefined()
  })

  it('renders Create Dashboard button', () => {
    render(<CustomDashboardsPage />, { wrapper })
    expect(screen.getByText('Create Dashboard')).toBeDefined()
  })

  it('shows create form when Create Dashboard clicked', () => {
    render(<CustomDashboardsPage />, { wrapper })
    fireEvent.click(screen.getByText('Create Dashboard'))
    expect(screen.getByPlaceholderText('Dashboard name')).toBeDefined()
    expect(screen.getByPlaceholderText('Description (optional)')).toBeDefined()
  })

  it('toggles create form to Cancel', () => {
    render(<CustomDashboardsPage />, { wrapper })
    fireEvent.click(screen.getByText('Create Dashboard'))
    expect(screen.getByText('Cancel')).toBeDefined()
    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByPlaceholderText('Dashboard name')).toBeNull()
  })

  it('calls delete mutation when Delete clicked', () => {
    render(<CustomDashboardsPage />, { wrapper })
    const deleteBtns = screen.getAllByText('Delete')
    fireEvent.click(deleteBtns[0])
    expect(mockDeleteMutate).toHaveBeenCalledWith('d1')
  })

  it('renders Edit buttons for each dashboard', () => {
    render(<CustomDashboardsPage />, { wrapper })
    const editBtns = screen.getAllByText('Edit')
    expect(editBtns.length).toBe(2)
  })
})
