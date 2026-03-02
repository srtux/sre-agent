import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import MessageItem from './MessageItem'
import type { ChatMessage } from '../../stores/chatStore'

vi.mock('./ToolCallInline', () => ({
  default: () => <div data-testid="tool-call">Tool</div>,
}))

vi.mock('./A2UISurfaceRenderer', () => ({
  default: () => <div data-testid="surface">Surface</div>,
}))

describe('MessageItem', () => {
  it('renders user message with content', () => {
    const msg: ChatMessage = {
      id: 'm1', role: 'user', content: 'Investigate latency',
      timestamp: new Date().toISOString(),
    }
    render(<MessageItem message={msg} />)
    expect(screen.getByText('Investigate latency')).toBeDefined()
  })

  it('renders assistant message with content', () => {
    const msg: ChatMessage = {
      id: 'm2', role: 'assistant',
      content: 'I will check the traces for high latency.',
      timestamp: new Date().toISOString(),
    }
    render(<MessageItem message={msg} />)
    expect(screen.getByText(/check the traces/)).toBeDefined()
  })

  it('renders tool calls when present', () => {
    const msg: ChatMessage = {
      id: 'm3', role: 'assistant', content: 'Analyzing...',
      timestamp: new Date().toISOString(),
      toolCalls: [{ toolName: 'get_traces', status: 'completed' }],
    }
    render(<MessageItem message={msg} />)
    expect(screen.getByTestId('tool-call')).toBeDefined()
  })
})
