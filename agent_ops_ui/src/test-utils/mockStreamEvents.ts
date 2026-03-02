/**
 * Factory functions for each NDJSON event type (for testing).
 */
import type {
  TextEvent,
  ErrorEvent,
  ToolCallEvent,
  ToolResponseEvent,
  A2UIEvent,
  DashboardEvent,
  TraceInfoEvent,
  MemoryEvent,
  SessionEvent,
  AgentActivityEvent,
  SuggestionsEvent,
} from '../types/streaming'

export function createTextEvent(content: string): TextEvent {
  return { type: 'text', content }
}

export function createErrorEvent(error: string): ErrorEvent {
  return { type: 'error', error }
}

export function createToolCallEvent(
  toolName: string,
  args?: Record<string, unknown>,
  callId?: string,
): ToolCallEvent {
  return {
    type: 'tool_call',
    tool_name: toolName,
    args,
    call_id: callId ?? `call-${Date.now()}`,
  }
}

export function createToolResponseEvent(
  toolName: string,
  result?: unknown,
  opts?: { callId?: string; duration?: number; status?: 'completed' | 'error' },
): ToolResponseEvent {
  return {
    type: 'tool_response',
    tool_name: toolName,
    result,
    call_id: opts?.callId ?? `call-${Date.now()}`,
    duration: opts?.duration ?? 150,
    status: opts?.status ?? 'completed',
  }
}

export function createA2UIEvent(
  action: 'beginRendering' | 'surfaceUpdate' | 'endRendering',
  surfaceId: string,
  componentName?: string,
  data?: Record<string, unknown>,
): A2UIEvent {
  return {
    type: 'a2ui',
    message: {
      action,
      surfaceId,
      componentName,
      data,
    },
  }
}

export function createDashboardEvent(
  widgetType: string,
  data: Record<string, unknown>,
  toolName = 'test_tool',
): DashboardEvent {
  return {
    type: 'dashboard',
    category: 'traces',
    widget_type: widgetType,
    tool_name: toolName,
    data,
  }
}

export function createTraceInfoEvent(
  traceId: string,
  traceUrl?: string,
): TraceInfoEvent {
  return {
    type: 'trace_info',
    trace_id: traceId,
    trace_url: traceUrl,
  }
}

export function createMemoryEvent(
  action: 'created' | 'updated' | 'deleted',
  title?: string,
): MemoryEvent {
  return { type: 'memory', action, title }
}

export function createSessionEvent(sessionId: string): SessionEvent {
  return { type: 'session', session_id: sessionId }
}

export function createAgentActivityEvent(
  agentName: string,
  phase?: string,
): AgentActivityEvent {
  return {
    type: 'agent_activity',
    agent: { agent_name: agentName },
    phase,
  }
}

export function createSuggestionsEvent(
  suggestions: string[],
): SuggestionsEvent {
  return { type: 'suggestions', suggestions }
}
