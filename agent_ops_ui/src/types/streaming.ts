/**
 * NDJSON stream event types — discriminated union for all backend event types.
 * Ported from autosre/lib/agent/adk_content_generator.dart
 */

export interface TextEvent {
  type: 'text'
  content: string
}

export interface ErrorEvent {
  type: 'error'
  error: string
}

export interface ToolCallEvent {
  type: 'tool_call'
  tool_name: string
  args?: Record<string, unknown>
  call_id?: string
}

export interface ToolResponseEvent {
  type: 'tool_response'
  tool_name: string
  result?: unknown
  call_id?: string
  duration?: number
  status?: 'completed' | 'error'
}

export interface A2UIEvent {
  type: 'a2ui'
  message: A2UIMessage
}

export interface A2UIMessage {
  action: 'beginRendering' | 'surfaceUpdate' | 'endRendering'
  surfaceId?: string
  componentName?: string
  data?: Record<string, unknown>
}

export interface DashboardEvent {
  type: 'dashboard'
  category: string
  widget_type: string
  tool_name: string
  data: Record<string, unknown>
}

export interface TraceInfoEvent {
  type: 'trace_info'
  trace_id: string
  trace_url?: string
}

export interface MemoryEvent {
  type: 'memory'
  action: 'created' | 'updated' | 'deleted'
  title?: string
  key?: string
}

export interface SessionEvent {
  type: 'session'
  session_id: string
}

export interface AgentActivityEvent {
  type: 'agent_activity'
  agent?: { agent_name: string }
  nodes?: Array<Record<string, unknown>>
  phase?: string
}

export interface CouncilGraphEvent {
  type: 'council_graph'
  investigation_id: string
  agents?: unknown[]
  edges?: unknown[]
}

export interface SuggestionsEvent {
  type: 'suggestions'
  suggestions: string[]
}

export interface UIEvent {
  type: 'ui'
  content: string
}

export type StreamEvent =
  | TextEvent
  | ErrorEvent
  | ToolCallEvent
  | ToolResponseEvent
  | A2UIEvent
  | DashboardEvent
  | TraceInfoEvent
  | MemoryEvent
  | SessionEvent
  | AgentActivityEvent
  | CouncilGraphEvent
  | SuggestionsEvent
  | UIEvent

// ─── Type Guards ─────────────────────────────────────────

export function isTextEvent(e: StreamEvent): e is TextEvent {
  return e.type === 'text'
}

export function isErrorEvent(e: StreamEvent): e is ErrorEvent {
  return e.type === 'error'
}

export function isToolCallEvent(e: StreamEvent): e is ToolCallEvent {
  return e.type === 'tool_call'
}

export function isToolResponseEvent(e: StreamEvent): e is ToolResponseEvent {
  return e.type === 'tool_response'
}

export function isA2UIEvent(e: StreamEvent): e is A2UIEvent {
  return e.type === 'a2ui'
}

export function isDashboardEvent(e: StreamEvent): e is DashboardEvent {
  return e.type === 'dashboard'
}

export function isTraceInfoEvent(e: StreamEvent): e is TraceInfoEvent {
  return e.type === 'trace_info'
}

export function isMemoryEvent(e: StreamEvent): e is MemoryEvent {
  return e.type === 'memory'
}

export function isSessionEvent(e: StreamEvent): e is SessionEvent {
  return e.type === 'session'
}

export function isAgentActivityEvent(e: StreamEvent): e is AgentActivityEvent {
  return e.type === 'agent_activity'
}

export function isCouncilGraphEvent(e: StreamEvent): e is CouncilGraphEvent {
  return e.type === 'council_graph'
}

export function isSuggestionsEvent(e: StreamEvent): e is SuggestionsEvent {
  return e.type === 'suggestions'
}
