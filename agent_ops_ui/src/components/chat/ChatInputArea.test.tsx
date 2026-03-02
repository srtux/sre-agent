import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatInputArea from './ChatInputArea'

vi.mock('../../hooks/usePromptHistory', () => ({
  usePromptHistory: () => ({
    add: vi.fn(),
    navigateUp: vi.fn().mockReturnValue('previous prompt'),
    navigateDown: vi.fn().mockReturnValue(null),
  }),
}))

describe('ChatInputArea', () => {
  const onSend = vi.fn()
  const onCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders textarea and send button', () => {
    render(<ChatInputArea onSend={onSend} onCancel={onCancel} isStreaming={false} />)
    expect(screen.getByRole('textbox')).toBeDefined()
    expect(screen.getByText('Send')).toBeDefined()
  })

  it('calls onSend with Enter key', () => {
    render(<ChatInputArea onSend={onSend} onCancel={onCancel} isStreaming={false} />)
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: 'Check traces' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })
    expect(onSend).toHaveBeenCalledWith('Check traces')
  })

  it('does not send on Shift+Enter (newline)', () => {
    render(<ChatInputArea onSend={onSend} onCancel={onCancel} isStreaming={false} />)
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: 'line1' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })
    expect(onSend).not.toHaveBeenCalled()
  })

  it('shows cancel button during streaming', () => {
    render(<ChatInputArea onSend={onSend} onCancel={onCancel} isStreaming={true} />)
    expect(screen.getByText('Cancel')).toBeDefined()
  })

  it('calls onCancel when cancel button clicked', () => {
    render(<ChatInputArea onSend={onSend} onCancel={onCancel} isStreaming={true} />)
    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalled()
  })
})
