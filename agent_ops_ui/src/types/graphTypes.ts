export type GraphEventType = 'THOUGHT' | 'TOOL_CALL' | 'OBSERVATION' | 'INCIDENT' | 'ACTION'

export interface ContextNode extends Record<string, unknown> {
  id: string
  type: GraphEventType
  label: string
  timestamp: string
  metadata?: {
    duration?: number
    tokenCount?: number
    [key: string]: unknown
  }
}

export interface ContextEdge {
  source: string
  target: string
  label?: string
}

export interface ContextStateDiff {
  workingMemory: Record<string, unknown>
  addedData: Record<string, unknown>
}

export interface ContextNodeProps {
  id: string
  type: string
  label: string
  diff: ContextStateDiff
}
