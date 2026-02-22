import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useDashboardFilters } from '../contexts/DashboardFilterContext'
import { useAgentContext } from '../contexts/AgentContext'

// --- Types ---

export interface ModelCallRow {
  modelName: string
  totalCalls: number
  p95Duration: number
  errorRate: number
  quotaExits: number
  tokensUsed: number
}

export interface ToolCallRow {
  toolName: string
  totalCalls: number
  p95Duration: number
  errorRate: number
}

export type LogSeverity = 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'

export interface AgentLogRow {
  timestamp: string
  agentId: string
  severity: LogSeverity
  message: string
  traceId: string
}

export interface DashboardTablesData {
  modelCalls: ModelCallRow[]
  toolCalls: ToolCallRow[]
  agentLogs: AgentLogRow[]
}

async function fetchDashboardTables(
  projectId: string,
  hours: number,
  serviceName: string,
): Promise<DashboardTablesData> {
  const params = {
    project_id: projectId,
    hours,
    service_name: serviceName || undefined,
  }

  const [modelsRes, toolsRes, logsRes] = await Promise.all([
    axios.get<{ modelCalls: ModelCallRow[] }>('/api/v1/graph/dashboard/models', {
      params,
    }),
    axios.get<{ toolCalls: ToolCallRow[] }>('/api/v1/graph/dashboard/tools', {
      params,
    }),
    axios.get<{ agentLogs: AgentLogRow[] }>('/api/v1/graph/dashboard/logs', {
      params,
    }),
  ])

  return {
    modelCalls: modelsRes.data.modelCalls,
    toolCalls: toolsRes.data.toolCalls,
    agentLogs: logsRes.data.agentLogs,
  }
}

// --- Hook ---

export function useDashboardTables(hours: number) {
  const { selectedAgents } = useDashboardFilters()
  const { projectId } = useAgentContext()
  const serviceName = selectedAgents.length > 0 ? selectedAgents[0] : ''

  return useQuery({
    queryKey: ['dashboard-tables', projectId, serviceName, hours],
    queryFn: () => fetchDashboardTables(projectId, hours, serviceName),
    enabled: !!projectId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}
