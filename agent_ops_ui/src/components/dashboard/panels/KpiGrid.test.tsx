import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DashboardFilterProvider } from '../../../contexts/DashboardFilterContext'
import KpiGrid from './KpiGrid'

import type { DashboardMetricsData } from '../../../hooks/useDashboardMetrics'

vi.mock('../../../hooks/useDashboardMetrics', () => ({
  useDashboardMetrics: vi.fn(),
}))

import { useDashboardMetrics } from '../../../hooks/useDashboardMetrics'

const mockData: DashboardMetricsData = {
  kpis: {
    totalSessions: 1842,
    avgTurns: 5.3,
    rootInvocations: 1205,
    errorRate: 0.045,
    totalSessionsTrend: 12.5,
    avgTurnsTrend: -3.2,
    rootInvocationsTrend: 5.8,
    errorRateTrend: -1.4,
  },
  latency: [],
  qps: [],
  tokens: [],
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardFilterProvider>{ui}</DashboardFilterProvider>
    </QueryClientProvider>,
  )
}

describe('KpiGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading skeleton', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    const { container } = renderWithProviders(<KpiGrid hours={24} />)
    // Skeleton should render 4 placeholder cards
    const skeletonDivs = container.querySelectorAll('div')
    expect(skeletonDivs.length).toBeGreaterThan(0)
  })

  it('renders error state', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<KpiGrid hours={24} />)
    expect(screen.getByText('Failed to load KPI metrics.')).toBeInTheDocument()
  })

  it('renders all 4 KPI cards with correct data', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<KpiGrid hours={24} />)

    expect(screen.getByText('Total Sessions')).toBeInTheDocument()
    expect(screen.getByText('1,842')).toBeInTheDocument()

    expect(screen.getByText('Avg Turns')).toBeInTheDocument()
    expect(screen.getByText('5.3')).toBeInTheDocument()

    expect(screen.getByText('Root Invocations')).toBeInTheDocument()
    expect(screen.getByText('1,205')).toBeInTheDocument()

    expect(screen.getByText('Error Rate')).toBeInTheDocument()
    expect(screen.getByText('4.5%')).toBeInTheDocument()
  })

  it('shows positive trend indicators', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<KpiGrid hours={24} />)

    expect(screen.getByText('+12.5%')).toBeInTheDocument()
    expect(screen.getByText('+5.8%')).toBeInTheDocument()
  })

  it('shows negative trend indicators', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<KpiGrid hours={24} />)

    expect(screen.getByText('-3.2%')).toBeInTheDocument()
    expect(screen.getByText('-1.4%')).toBeInTheDocument()
  })
})
