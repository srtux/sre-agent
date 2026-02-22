import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useDashboardFilters } from '../contexts/DashboardFilterContext'
import { useAgentContext } from '../contexts/AgentContext'

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

const timeRangeToHours: Record<string, number> = {
  '1h': 1,
  '6h': 6,
  '24h': 24,
  '7d': 168,
  '30d': 720,
}

async function fetchDashboardMetrics(
  projectId: string,
  hours: number,
  serviceName: string,
): Promise<DashboardMetricsData> {
  const params = {
    project_id: projectId,
    hours,
    service_name: serviceName || undefined,
  }

  const [kpiRes, tsRes] = await Promise.all([
    axios.get<{ kpis: KpiMetrics }>('/api/v1/graph/dashboard/kpis', { params }),
    axios.get<{ latency: LatencyPoint[]; qps: QpsPoint[]; tokens: TokenPoint[] }>(
      '/api/v1/graph/dashboard/timeseries',
      { params },
    ),
  ])

  return {
    kpis: kpiRes.data.kpis,
    latency: tsRes.data.latency,
    qps: tsRes.data.qps,
    tokens: tsRes.data.tokens,
  }
}

export function useDashboardMetrics() {
  const { timeRange } = useDashboardFilters()
  const { projectId, serviceName } = useAgentContext()
  const hours = timeRangeToHours[timeRange] ?? 24

  return useQuery({
    queryKey: ['dashboard-metrics', projectId, serviceName, timeRange],
    queryFn: () => fetchDashboardMetrics(projectId, hours, serviceName),
    enabled: !!projectId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}
