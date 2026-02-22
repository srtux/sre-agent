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

export interface AgentSessionRow {
  timestamp: string
  sessionId: string
  turns: number
  latestTraceId: string
  totalTokens: number
  errorCount: number
  avgLatencyMs: number
  p95LatencyMs: number
}

export interface AgentTraceRow {
  timestamp: string
  traceId: string
  sessionId: string
  totalTokens: number
  errorCount: number
  latencyMs: number
}

export interface DashboardTablesData {
  modelCalls: ModelCallRow[]
  toolCalls: ToolCallRow[]
  agentLogs: AgentLogRow[]
  agentSessions: AgentSessionRow[]
  agentTraces: AgentTraceRow[]
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

  const [modelsRes, toolsRes, logsRes, sessionsRes, tracesRes] = await Promise.all([
    axios.get<{ modelCalls: ModelCallRow[] }>('/api/v1/graph/dashboard/models', {
      params,
    }),
    axios.get<{ toolCalls: ToolCallRow[] }>('/api/v1/graph/dashboard/tools', {
      params,
    }),
    axios.get<{ agentLogs: AgentLogRow[] }>('/api/v1/graph/dashboard/logs', {
      params,
    }),
    axios.get<{ agentSessions: AgentSessionRow[] }>('/api/v1/graph/dashboard/sessions', {
      params,
    }),
    axios.get<{ agentTraces: AgentTraceRow[] }>('/api/v1/graph/dashboard/traces', {
      params,
    }),
  ])

  return {
    modelCalls: modelsRes.data.modelCalls,
    toolCalls: toolsRes.data.toolCalls,
    agentLogs: logsRes.data.agentLogs,
    agentSessions: sessionsRes.data.agentSessions,
    agentTraces: tracesRes.data.agentTraces,
  }
}

// --- Hook ---

export function useDashboardTables(hours: number, explicitServiceName?: string) {
  const { selectedAgents } = useDashboardFilters()
  const { projectId } = useAgentContext()
  const serviceName = explicitServiceName !== undefined
    ? explicitServiceName
    : (selectedAgents.length > 0 ? selectedAgents[0] : '')

  return useQuery({
    queryKey: ['dashboard-tables', projectId, serviceName, hours],
    queryFn: () => fetchDashboardTables(projectId, hours, serviceName),
    enabled: !!projectId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}
