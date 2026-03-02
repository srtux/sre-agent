import { describe, it, expect, beforeEach } from 'vitest'
import { useChatStore, generateMessageId } from './chatStore'

describe('chatStore', () => {
  beforeEach(() => {
    useChatStore.setState({
      messages: [],
      isStreaming: false,
      isProcessing: false,
      abortController: null,
      surfaces: new Map(),
      activeToolCalls: new Map(),
      suggestions: [],
      error: null,
    })
  })

  describe('message management', () => {
    it('addMessage appends a message', () => {
      useChatStore.getState().addMessage({
        id: generateMessageId(), role: 'user', content: 'Hello',
        timestamp: new Date().toISOString(),
      })
      expect(useChatStore.getState().messages).toHaveLength(1)
      expect(useChatStore.getState().messages[0].content).toBe('Hello')
    })

    it('appendToLastAssistant appends text', () => {
      useChatStore.getState().addMessage({
        id: 'm1', role: 'assistant', content: 'Start',
        timestamp: new Date().toISOString(),
      })
      useChatStore.getState().appendToLastAssistant(' end')
      expect(useChatStore.getState().messages[0].content).toBe('Start end')
    })

    it('updateLastAssistant applies updater function', () => {
      useChatStore.getState().addMessage({
        id: 'm1', role: 'assistant', content: 'original',
        timestamp: new Date().toISOString(),
      })
      useChatStore.getState().updateLastAssistant((msg) => ({
        ...msg, content: 'updated',
      }))
      expect(useChatStore.getState().messages[0].content).toBe('updated')
    })

    it('clearMessages resets all state', () => {
      useChatStore.getState().addMessage({
        id: 'm1', role: 'user', content: 'test',
        timestamp: new Date().toISOString(),
      })
      useChatStore.getState().setSuggestions(['s1'])
      useChatStore.getState().clearMessages()

      const state = useChatStore.getState()
      expect(state.messages).toHaveLength(0)
      expect(state.suggestions).toHaveLength(0)
      expect(state.surfaces.size).toBe(0)
    })
  })

  describe('streaming control', () => {
    it('startStreaming sets streaming state', () => {
      const ac = new AbortController()
      useChatStore.getState().startStreaming(ac)
      expect(useChatStore.getState().isStreaming).toBe(true)
      expect(useChatStore.getState().abortController).toBe(ac)
    })

    it('stopStreaming clears streaming state', () => {
      useChatStore.getState().startStreaming(new AbortController())
      useChatStore.getState().stopStreaming()
      expect(useChatStore.getState().isStreaming).toBe(false)
      expect(useChatStore.getState().abortController).toBeNull()
    })

    it('cancelStream aborts and resets', () => {
      const ac = new AbortController()
      useChatStore.getState().startStreaming(ac)
      useChatStore.getState().cancelStream()
      expect(ac.signal.aborted).toBe(true)
      expect(useChatStore.getState().isStreaming).toBe(false)
    })
  })

  describe('A2UI surfaces', () => {
    it('beginSurface creates a new surface', () => {
      useChatStore.getState().beginSurface('s1', 'x-sre-trace', { traceId: 't1' })
      const s = useChatStore.getState().surfaces.get('s1')
      expect(s).toBeDefined()
      expect(s?.componentName).toBe('x-sre-trace')
      expect(s?.status).toBe('rendering')
    })

    it('updateSurface merges data', () => {
      useChatStore.getState().beginSurface('s1', 'x-sre-trace', { a: 1 })
      useChatStore.getState().updateSurface('s1', { b: 2 })
      const s = useChatStore.getState().surfaces.get('s1')
      expect(s?.data).toEqual({ a: 1, b: 2 })
    })

    it('endSurface marks as complete', () => {
      useChatStore.getState().beginSurface('s1', 'x-sre-trace')
      useChatStore.getState().endSurface('s1')
      expect(useChatStore.getState().surfaces.get('s1')?.status).toBe('complete')
    })
  })

  describe('tool calls', () => {
    it('startToolCall creates running tool', () => {
      useChatStore.getState().startToolCall('c1', 'get_traces', { filter: 'x' })
      const tc = useChatStore.getState().activeToolCalls.get('c1')
      expect(tc?.toolName).toBe('get_traces')
      expect(tc?.status).toBe('running')
    })

    it('completeToolCall sets completed with result', () => {
      useChatStore.getState().startToolCall('c1', 'get_traces')
      useChatStore.getState().completeToolCall('c1', { count: 5 }, 200)
      const tc = useChatStore.getState().activeToolCalls.get('c1')
      expect(tc?.status).toBe('completed')
      expect(tc?.result).toEqual({ count: 5 })
      expect(tc?.duration).toBe(200)
    })

    it('failToolCall sets error status', () => {
      useChatStore.getState().startToolCall('c1', 'get_traces')
      useChatStore.getState().failToolCall('c1', 'timeout')
      const tc = useChatStore.getState().activeToolCalls.get('c1')
      expect(tc?.status).toBe('error')
      expect(tc?.result).toBe('timeout')
    })
  })

  describe('suggestions', () => {
    it('setSuggestions and clearSuggestions work', () => {
      useChatStore.getState().setSuggestions(['a', 'b'])
      expect(useChatStore.getState().suggestions).toEqual(['a', 'b'])
      useChatStore.getState().clearSuggestions()
      expect(useChatStore.getState().suggestions).toHaveLength(0)
    })
  })

  describe('generateMessageId', () => {
    it('returns unique IDs', () => {
      const a = generateMessageId()
      const b = generateMessageId()
      expect(a).not.toBe(b)
      expect(a).toMatch(/^msg-/)
    })
  })
})
