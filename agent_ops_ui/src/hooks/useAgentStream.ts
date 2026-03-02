/**
 * NDJSON streaming hook for agent chat.
 * Uses fetch() + ReadableStream + AbortController, dispatching events to Zustand stores.
 * Ported from autosre/lib/agent/adk_content_generator.dart
 */
import { useCallback } from 'react'
import { parseNDJSONStream } from '../utils/ndjsonParser'
import { useChatStore, generateMessageId } from '../stores/chatStore'
import { useDashboardStore } from '../stores/dashboardStore'
import { useSessionStore } from '../stores/sessionStore'
import { useAuthStore } from '../stores/authStore'
import { useProjectStore } from '../stores/projectStore'
import type { StreamEvent } from '../types/streaming'

interface SendOptions {
  message: string
  sessionId?: string
}

export function useAgentStream() {
  const sendMessage = useCallback(async ({ message, sessionId }: SendOptions) => {
    const chatStore = useChatStore.getState()
    const authStore = useAuthStore.getState()
    const projectStore = useProjectStore.getState()

    // Add user message
    chatStore.addMessage({
      id: generateMessageId(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    })

    // Create assistant placeholder
    chatStore.addMessage({
      id: generateMessageId(),
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    })

    const abortController = new AbortController()
    chatStore.startStreaming(abortController)
    chatStore.setProcessing(true)

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }

      if (authStore.isGuest) {
        headers['X-Guest-Mode'] = 'true'
        headers['Authorization'] = 'Bearer dev-mode-bypass-token'
      } else if (authStore.accessToken) {
        headers['Authorization'] = `Bearer ${authStore.accessToken}`
      }

      if (projectStore.projectId) {
        headers['X-GCP-Project-ID'] = projectStore.projectId
      }

      const url = sessionId
        ? `/api/sessions/${sessionId}/agent`
        : '/api/agent'

      const response = await fetch(url, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({ message }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      if (!response.body) {
        throw new Error('Response body is null')
      }

      for await (const event of parseNDJSONStream(response.body)) {
        dispatchEvent(event)
      }

      // Mark last assistant message as done streaming
      chatStore.updateLastAssistant((msg) => ({
        ...msg,
        isStreaming: false,
      }))
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        chatStore.appendToLastAssistant('\n\n*[Request cancelled]*')
      } else {
        chatStore.setError((err as Error).message)
        chatStore.appendToLastAssistant(
          `\n\n**Error:** ${(err as Error).message}`,
        )
      }
    } finally {
      chatStore.stopStreaming()
    }
  }, [])

  const cancel = useCallback(() => {
    useChatStore.getState().cancelStream()
  }, [])

  return { sendMessage, cancel }
}

function dispatchEvent(event: StreamEvent): void {
  const chat = useChatStore.getState()
  const dashboard = useDashboardStore.getState()
  const session = useSessionStore.getState()

  switch (event.type) {
    case 'text':
      chat.appendToLastAssistant(event.content)
      break

    case 'error':
      chat.setError(event.error)
      chat.appendToLastAssistant(`\n\n**Error:** ${event.error}`)
      break

    case 'tool_call':
      if (event.call_id) {
        chat.startToolCall(event.call_id, event.tool_name, event.args)
      }
      break

    case 'tool_response':
      if (event.call_id) {
        if (event.status === 'error') {
          chat.failToolCall(event.call_id, String(event.result))
        } else {
          chat.completeToolCall(event.call_id, event.result, event.duration)
        }
      }
      break

    case 'a2ui': {
      const msg = event.message
      if (msg.action === 'beginRendering' && msg.surfaceId && msg.componentName) {
        chat.beginSurface(msg.surfaceId, msg.componentName, msg.data)
      } else if (msg.action === 'surfaceUpdate' && msg.surfaceId && msg.data) {
        chat.updateSurface(msg.surfaceId, msg.data)
      } else if (msg.action === 'endRendering' && msg.surfaceId) {
        chat.endSurface(msg.surfaceId)
      }
      break
    }

    case 'dashboard':
      dashboard.addFromEvent(event as unknown as Record<string, unknown>)
      break

    case 'session':
      session.setCurrentSession(event.session_id)
      break

    case 'suggestions':
      chat.setSuggestions(event.suggestions)
      break

    case 'trace_info':
      chat.updateLastAssistant((msg) => ({
        ...msg,
        traceId: event.trace_id,
        traceUrl: event.trace_url,
      }))
      break

    case 'memory':
      // Memory events are handled by MemoryToast (component listens to stream)
      break

    case 'agent_activity':
      dashboard.addFromEvent({
        widget_type: 'x-sre-agent-activity',
        tool_name: event.agent?.agent_name || 'agent',
        data: event,
      })
      break

    case 'council_graph':
      dashboard.addFromEvent({
        widget_type: 'x-sre-agent-graph',
        tool_name: 'council',
        data: event,
      })
      break
  }
}
