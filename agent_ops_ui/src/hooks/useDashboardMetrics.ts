import { useQuery } from '@tanstack/react-query'
import { useDashboardFilters } from '../contexts/DashboardFilterContext'

export interface KpiMetrics {
  totalSessions: number
  avgTurns: number
  rootInvocations: number
  errorRate: number
  totalSessionsTrend: number
  avgTurnsTrend: number
  rootInvocationsTrend: number
  errorRateTrend: number
}

export interface LatencyPoint {
  timestamp: string
  p50: number
  p95: number
}

export interface QpsPoint {
  timestamp: string
  qps: number
  errorRate: number
}

export interface TokenPoint {
  timestamp: string
  input: number
  output: number
}

export interface DashboardMetricsData {
  kpis: KpiMetrics
  latency: LatencyPoint[]
  qps: QpsPoint[]
  tokens: TokenPoint[]
}

const timeRangeToPoints: Record<string, number> = {
  '1h': 12,
  '6h': 36,
  '24h': 48,
  '7d': 84,
  '30d': 120,
}

const timeRangeToMs: Record<string, number> = {
  '1h': 60 * 60 * 1000,
  '6h': 6 * 60 * 60 * 1000,
  '24h': 24 * 60 * 60 * 1000,
  '7d': 7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
}

function generateTimestamps(pointCount: number, durationMs: number): string[] {
  const now = Date.now()
  const interval = durationMs / (pointCount - 1)
  return Array.from({ length: pointCount }, (_, i) => {
    return new Date(now - (pointCount - 1 - i) * interval).toISOString()
  })
}

// TODO: Replace mock data with real API calls when backend endpoints are ready:
//   POST /api/dashboards/agents/kpis — pass timeRange + selectedAgents
//   POST /api/dashboards/agents/timeseries — pass timeRange + selectedAgents
async function fetchDashboardMetrics(
  timeRange: string,
): Promise<DashboardMetricsData> {
  await new Promise((resolve) => setTimeout(resolve, 400))

  const pointCount = timeRangeToPoints[timeRange] ?? 48
  const durationMs = timeRangeToMs[timeRange] ?? timeRangeToMs['24h']
  const timestamps = generateTimestamps(pointCount, durationMs)

  const kpis: KpiMetrics = {
    totalSessions: 1800 + Math.round(600 * Math.sin(pointCount * 0.1)),
    avgTurns: 5 + Math.round(2 * Math.sin(pointCount * 0.3) * 10) / 10,
    rootInvocations: 1200 + Math.round(400 * Math.cos(pointCount * 0.2)),
    errorRate: 0.045 + 0.035 * Math.sin(pointCount * 0.15),
    totalSessionsTrend: 12.5,
    avgTurnsTrend: -3.2,
    rootInvocationsTrend: 5.8,
    errorRateTrend: -1.4,
  }

  const latency: LatencyPoint[] = timestamps.map((timestamp, i) => ({
    timestamp,
    p50: 160 + 40 * Math.sin(i * 0.5) + (i % 7) * 2,
    p95: 475 + 125 * Math.sin(i * 0.3) + (i % 11) * 5,
  }))

  const qps: QpsPoint[] = timestamps.map((timestamp, i) => ({
    timestamp,
    qps: 100 + 50 * Math.sin(i * 0.4) + (i % 5) * 3,
    errorRate: 0.02 + 0.03 * Math.abs(Math.sin(i * 0.6)),
  }))

  const tokens: TokenPoint[] = timestamps.map((timestamp, i) => ({
    timestamp,
    input: 22500 + 7500 * Math.sin(i * 0.35) + (i % 9) * 200,
    output: 14000 + 6000 * Math.sin(i * 0.45) + (i % 13) * 150,
  }))

  return { kpis, latency, qps, tokens }
}

export function useDashboardMetrics() {
  const { timeRange, selectedAgents } = useDashboardFilters()

  return useQuery({
    queryKey: ['dashboard-metrics', timeRange, selectedAgents],
    queryFn: () => fetchDashboardMetrics(timeRange),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}
