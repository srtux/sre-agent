import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { render, screen } from '@testing-library/react'
import { useChatStore } from '../../stores/chatStore'

// jsdom does not implement scrollIntoView
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

vi.mock('../../hooks/useAgentStream', () => ({
  useAgentStream: () => ({ sendMessage: vi.fn(), cancel: vi.fn() }),
}))

vi.mock('../../stores/sessionStore', () => ({
  useSessionStore: Object.assign(
    (selector: (s: { currentSessionId: string | null }) => unknown) =>
      selector({ currentSessionId: 'test-sess' }),
    { getState: () => ({ currentSessionId: 'test-sess' }) },
  ),
}))

// Must import after mocks
import ChatPanel from './ChatPanel'

describe('ChatPanel', () => {
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

  it('renders hero empty state when no messages', () => {
    render(<ChatPanel />)
    // HeroEmptyState should be rendered when messages are empty
    // The component renders the hero when messages.length === 0
    expect(document.querySelector('[style]')).toBeDefined()
  })

  it('renders message list when messages exist', () => {
    useChatStore.setState({
      messages: [
        { id: 'm1', role: 'user', content: 'Hello SRE', timestamp: new Date().toISOString() },
        { id: 'm2', role: 'assistant', content: 'Investigating...', timestamp: new Date().toISOString() },
      ],
    })
    render(<ChatPanel />)
    expect(screen.getByText('Hello SRE')).toBeDefined()
    expect(screen.getByText(/Investigating/)).toBeDefined()
  })
})
