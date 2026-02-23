import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useAgentContext } from '../contexts/AgentContext'
import { useDashboardFilters } from '../contexts/DashboardFilterContext'
import type { EvalMetricPoint, EvalMetricsAggregateResponse } from '../types'

async function fetchEvalMetrics(
  projectId: string,
  hours: number,
  serviceName: string,
): Promise<EvalMetricPoint[]> {
  const params = {
    project_id: projectId,
    hours,
    service_name: serviceName || undefined,
  }

  const res = await axios.get<EvalMetricsAggregateResponse>(
    '/api/v1/evals/metrics/aggregate',
    { params },
  )

  return res.data.metrics
}

export function useEvalMetrics(hours: number) {
  const { selectedAgents } = useDashboardFilters()
  const { projectId } = useAgentContext()
  const serviceName = selectedAgents.length > 0 ? selectedAgents[0] : ''

  return useQuery({
    queryKey: ['eval-metrics', projectId, serviceName, hours],
    queryFn: () => fetchEvalMetrics(projectId, hours, serviceName),
    enabled: !!projectId,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })
}
