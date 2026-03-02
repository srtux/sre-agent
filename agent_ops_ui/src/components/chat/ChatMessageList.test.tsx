import { describe, it, expect, vi, beforeAll } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChatMessageList from './ChatMessageList'
import type { ChatMessage } from '../../stores/chatStore'

// jsdom does not implement scrollIntoView
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

// Mock MessageItem to isolate this test
vi.mock('./MessageItem', () => ({
  default: ({ message }: { message: ChatMessage }) => (
    <div data-testid={`msg-${message.id}`}>{message.content}</div>
  ),
}))

describe('ChatMessageList', () => {
  const messages: ChatMessage[] = [
    { id: 'm1', role: 'user', content: 'First message', timestamp: '2026-01-01T00:00:00Z' },
    { id: 'm2', role: 'assistant', content: 'Second message', timestamp: '2026-01-01T00:00:01Z' },
    { id: 'm3', role: 'user', content: 'Third message', timestamp: '2026-01-01T00:00:02Z' },
  ]

  it('renders all messages', () => {
    render(<ChatMessageList messages={messages} />)
    expect(screen.getByTestId('msg-m1')).toBeDefined()
    expect(screen.getByTestId('msg-m2')).toBeDefined()
    expect(screen.getByTestId('msg-m3')).toBeDefined()
  })

  it('renders correct content for each message', () => {
    render(<ChatMessageList messages={messages} />)
    expect(screen.getByText('First message')).toBeDefined()
    expect(screen.getByText('Second message')).toBeDefined()
    expect(screen.getByText('Third message')).toBeDefined()
  })

  it('renders empty list without errors', () => {
    const { container } = render(<ChatMessageList messages={[]} />)
    expect(container.firstChild).toBeDefined()
  })
})
