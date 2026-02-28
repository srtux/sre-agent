import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAgentContext } from '../contexts/AgentContext'

export interface TrajectoryEvaluation {
  metricName: string
  score: number
  explanation: string
}

export interface TrajectoryLog {
  timestamp: string | null
  severity: string
  payload: string | Record<string, unknown>
}

export interface TrajectoryEvent {
  traceId: string
  spanId: string
  parentSpanId: string | null
  startTime: string | null
  nodeType: string
  nodeLabel: string
  durationMs: number
  statusCode: number
  statusMessage: string | null
  inputTokens: number
  outputTokens: number
  totalTokens: number
  model: string | null
  prompt: string | null
  completion: string | null
  systemMessage: string | null
  toolInput: string | null
  toolOutput: string | null
  evaluations: TrajectoryEvaluation[]
  logs: TrajectoryLog[]
}

export interface SessionTrajectoryData {
  sessionId: string
  trajectory: TrajectoryEvent[]
}

export function useSessionTrajectory(sessionId: string | null, activeTab: string, viewMode: string) {
  const { projectId } = useAgentContext()
  const [data, setData] = useState<SessionTrajectoryData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    // Only fetch if we are on the log mode for traces and a session is selected
    if (!sessionId || !projectId || activeTab !== 'traces' || viewMode !== 'log') {
      return
    }

    let isMounted = true
    setLoading(true)
    setError(null)

    axios
      .get<SessionTrajectoryData>(`/api/v1/graph/session/${sessionId}/trajectory`, {
        params: { project_id: projectId },
      })
      .then((res) => {
        if (isMounted) {
          setData(res.data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err)
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [sessionId, projectId, activeTab, viewMode])

  return { data, loading, error }
}
