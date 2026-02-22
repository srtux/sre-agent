import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DashboardFilterProvider } from '../../../contexts/DashboardFilterContext'
import InteractionMetricsPanel from './InteractionMetricsPanel'

import type { DashboardMetricsData } from '../../../hooks/useDashboardMetrics'

// Mock EChartWrapper to avoid echarts DOM rendering in test
vi.mock('../../charts/EChartWrapper', () => ({
  default: function MockEChartWrapper({
    loading,
    option,
  }: {
    loading?: boolean
    option: { series?: Array<{ name?: string }> }
  }) {
    if (loading) return <div data-testid="chart-loading">Loading chart...</div>
    const seriesNames =
      option.series?.map((s) => s.name).filter(Boolean) ?? []
    return (
      <div data-testid="chart">
        {seriesNames.map((name) => (
          <span key={name} data-testid={`series-${name}`}>
            {name}
          </span>
        ))}
      </div>
    )
  },
}))

vi.mock('../../../hooks/useDashboardMetrics', () => ({
  useDashboardMetrics: vi.fn(),
}))

import { useDashboardMetrics } from '../../../hooks/useDashboardMetrics'

const mockData: DashboardMetricsData = {
  kpis: {
    totalSessions: 100,
    avgTurns: 5,
    rootInvocations: 80,
    errorRate: 0.05,
    totalSessionsTrend: 0,
    avgTurnsTrend: 0,
    rootInvocationsTrend: 0,
    errorRateTrend: 0,
  },
  latency: [
    { timestamp: '2026-02-21T10:00:00.000Z', p50: 150, p95: 450 },
    { timestamp: '2026-02-21T11:00:00.000Z', p50: 160, p95: 470 },
  ],
  qps: [
    { timestamp: '2026-02-21T10:00:00.000Z', qps: 120, errorRate: 0.03 },
    { timestamp: '2026-02-21T11:00:00.000Z', qps: 130, errorRate: 0.04 },
  ],
  tokens: [
    { timestamp: '2026-02-21T10:00:00.000Z', input: 20000, output: 12000 },
    { timestamp: '2026-02-21T11:00:00.000Z', input: 22000, output: 14000 },
  ],
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

describe('InteractionMetricsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state for all charts', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<InteractionMetricsPanel />)
    const loadingCharts = screen.getAllByTestId('chart-loading')
    expect(loadingCharts).toHaveLength(3)
  })

  it('renders section headers', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<InteractionMetricsPanel />)
    expect(screen.getByText('Latency Over Time')).toBeInTheDocument()
    expect(screen.getByText('QPS & Error Rate')).toBeInTheDocument()
    expect(screen.getByText('Token Usage')).toBeInTheDocument()
  })

  it('renders latency chart with P50 and P95 series', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<InteractionMetricsPanel />)
    expect(screen.getByTestId('series-P50')).toBeInTheDocument()
    expect(screen.getByTestId('series-P95')).toBeInTheDocument()
  })

  it('renders QPS chart with QPS and Error Rate series', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<InteractionMetricsPanel />)
    expect(screen.getByTestId('series-QPS')).toBeInTheDocument()
    expect(screen.getByTestId('series-Error Rate')).toBeInTheDocument()
  })

  it('renders token chart with Input and Output series', () => {
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<InteractionMetricsPanel />)
    expect(screen.getByTestId('series-Input Tokens')).toBeInTheDocument()
    expect(screen.getByTestId('series-Output Tokens')).toBeInTheDocument()
  })

  it('renders empty charts when data has no series', () => {
    const emptyData: DashboardMetricsData = {
      ...mockData,
      latency: [],
      qps: [],
      tokens: [],
    }
    vi.mocked(useDashboardMetrics).mockReturnValue({
      data: emptyData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardMetrics>)

    renderWithProviders(<InteractionMetricsPanel />)
    // Charts should still render without series names
    const charts = screen.getAllByTestId('chart')
    expect(charts).toHaveLength(3)
  })
})
