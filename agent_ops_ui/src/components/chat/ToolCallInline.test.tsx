import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ToolCallInline from './ToolCallInline'
import type { ToolLog } from '../../types/sre'

describe('ToolCallInline', () => {
  it('renders running state with spinner', () => {
    const tc: ToolLog = { toolName: 'get_traces', status: 'running', args: { project_id: 'p1' } }
    render(<ToolCallInline toolCall={tc} />)
    expect(screen.getByText('get_traces')).toBeDefined()
  })

  it('renders completed state with duration', () => {
    const tc: ToolLog = {
      toolName: 'get_logs', status: 'completed',
      result: { count: 42 }, duration: 250,
    }
    render(<ToolCallInline toolCall={tc} />)
    expect(screen.getByText('get_logs')).toBeDefined()
    expect(screen.getByText(/250/)).toBeDefined()
  })

  it('renders error state', () => {
    const tc: ToolLog = {
      toolName: 'failing_tool', status: 'error',
      result: 'Connection refused',
    }
    render(<ToolCallInline toolCall={tc} />)
    expect(screen.getByText('failing_tool')).toBeDefined()
  })

  it('expands to show args and result on click', () => {
    const tc: ToolLog = {
      toolName: 'get_traces', status: 'completed',
      args: { project_id: 'test-proj' },
      result: { trace_count: 5 },
      duration: 100,
    }
    render(<ToolCallInline toolCall={tc} />)
    fireEvent.click(screen.getByText('get_traces'))
    expect(screen.getByText(/test-proj/)).toBeDefined()
  })
})
