/**
 * Chat state store (Zustand).
 * Manages messages, streaming, A2UI surfaces, and tool calls.
 * Ported from autosre/lib/pages/conversation_controller.dart
 */
import { create } from 'zustand'
import type { ToolLog } from '../types/sre'
import type { Surface } from '../types/a2ui'

export type MessageRole = 'user' | 'assistant' | 'system'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  timestamp: string
  toolCalls?: ToolLog[]
  surfaces?: Surface[]
  suggestions?: string[]
  traceId?: string
  traceUrl?: string
  isStreaming?: boolean
}

interface ChatState {
  messages: ChatMessage[]
  isStreaming: boolean
  isProcessing: boolean
  abortController: AbortController | null
  surfaces: Map<string, Surface>
  activeToolCalls: Map<string, ToolLog>
  suggestions: string[]
  error: string | null

  // Message management
  addMessage: (msg: ChatMessage) => void
  appendToLastAssistant: (text: string) => void
  updateLastAssistant: (updater: (msg: ChatMessage) => ChatMessage) => void
  clearMessages: () => void

  // Streaming control
  startStreaming: (abortController: AbortController) => void
  stopStreaming: () => void
  setProcessing: (processing: boolean) => void
  cancelStream: () => void

  // A2UI surfaces
  beginSurface: (id: string, componentName: string, data?: Record<string, unknown>) => void
  updateSurface: (id: string, data: Record<string, unknown>) => void
  endSurface: (id: string) => void

  // Tool calls
  startToolCall: (callId: string, toolName: string, args?: Record<string, unknown>) => void
  completeToolCall: (callId: string, result?: unknown, duration?: number) => void
  failToolCall: (callId: string, error?: string) => void

  // Suggestions
  setSuggestions: (suggestions: string[]) => void
  clearSuggestions: () => void

  // Error
  setError: (error: string | null) => void
}

let messageCounter = 0
export function generateMessageId(): string {
  return `msg-${Date.now()}-${++messageCounter}`
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  isProcessing: false,
  abortController: null,
  surfaces: new Map(),
  activeToolCalls: new Map(),
  suggestions: [],
  error: null,

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  appendToLastAssistant: (text) =>
    set((state) => {
      const msgs = [...state.messages]
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant') {
          msgs[i] = { ...msgs[i], content: msgs[i].content + text }
          break
        }
      }
      return { messages: msgs }
    }),

  updateLastAssistant: (updater) =>
    set((state) => {
      const msgs = [...state.messages]
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant') {
          msgs[i] = updater(msgs[i])
          break
        }
      }
      return { messages: msgs }
    }),

  clearMessages: () =>
    set({
      messages: [],
      surfaces: new Map(),
      activeToolCalls: new Map(),
      suggestions: [],
      error: null,
    }),

  startStreaming: (abortController) =>
    set({ isStreaming: true, abortController, error: null }),

  stopStreaming: () =>
    set({
      isStreaming: false,
      isProcessing: false,
      abortController: null,
    }),

  setProcessing: (processing) => set({ isProcessing: processing }),

  cancelStream: () => {
    const { abortController } = get()
    abortController?.abort()
    set({ isStreaming: false, isProcessing: false, abortController: null })
  },

  beginSurface: (id, componentName, data) =>
    set((state) => {
      const surfaces = new Map(state.surfaces)
      surfaces.set(id, {
        id,
        componentName,
        data: data ?? {},
        status: 'rendering',
      })
      return { surfaces }
    }),

  updateSurface: (id, data) =>
    set((state) => {
      const surfaces = new Map(state.surfaces)
      const existing = surfaces.get(id)
      if (existing) {
        surfaces.set(id, { ...existing, data: { ...existing.data, ...data } })
      }
      return { surfaces }
    }),

  endSurface: (id) =>
    set((state) => {
      const surfaces = new Map(state.surfaces)
      const existing = surfaces.get(id)
      if (existing) {
        surfaces.set(id, { ...existing, status: 'complete' })
      }
      return { surfaces }
    }),

  startToolCall: (callId, toolName, args) =>
    set((state) => {
      const activeToolCalls = new Map(state.activeToolCalls)
      activeToolCalls.set(callId, {
        toolName,
        args,
        status: 'running',
        timestamp: new Date().toISOString(),
      })
      return { activeToolCalls }
    }),

  completeToolCall: (callId, result, duration) =>
    set((state) => {
      const activeToolCalls = new Map(state.activeToolCalls)
      const existing = activeToolCalls.get(callId)
      if (existing) {
        activeToolCalls.set(callId, {
          ...existing,
          status: 'completed',
          result,
          duration,
        })
      }
      return { activeToolCalls }
    }),

  failToolCall: (callId, error) =>
    set((state) => {
      const activeToolCalls = new Map(state.activeToolCalls)
      const existing = activeToolCalls.get(callId)
      if (existing) {
        activeToolCalls.set(callId, {
          ...existing,
          status: 'error',
          result: error,
        })
      }
      return { activeToolCalls }
    }),

  setSuggestions: (suggestions) => set({ suggestions }),
  clearSuggestions: () => set({ suggestions: [] }),

  setError: (error) => set({ error }),
}))
