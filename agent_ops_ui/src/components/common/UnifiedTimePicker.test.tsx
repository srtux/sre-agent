import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import UnifiedTimePicker from './UnifiedTimePicker'

describe('UnifiedTimePicker', () => {
  const onChange = vi.fn()
  const baseRange = {
    start: new Date('2026-02-28T12:00:00Z'),
    end: new Date('2026-02-28T13:00:00Z'),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all preset buttons', () => {
    render(<UnifiedTimePicker value={baseRange} onChange={onChange} />)
    expect(screen.getByText('15m')).toBeDefined()
    expect(screen.getByText('1h')).toBeDefined()
    expect(screen.getByText('6h')).toBeDefined()
    expect(screen.getByText('24h')).toBeDefined()
    expect(screen.getByText('7d')).toBeDefined()
    expect(screen.getByText('30d')).toBeDefined()
  })

  it('renders "to" separator between datetime inputs', () => {
    render(<UnifiedTimePicker value={baseRange} onChange={onChange} />)
    expect(screen.getByText('to')).toBeDefined()
  })

  it('renders two datetime-local inputs', () => {
    const { container } = render(<UnifiedTimePicker value={baseRange} onChange={onChange} />)
    const inputs = container.querySelectorAll('input[type="datetime-local"]')
    expect(inputs.length).toBe(2)
  })

  it('calls onChange when preset button clicked', () => {
    render(<UnifiedTimePicker value={baseRange} onChange={onChange} />)
    fireEvent.click(screen.getByText('24h'))
    expect(onChange).toHaveBeenCalledTimes(1)
    const call = onChange.mock.calls[0][0]
    expect(call.start).toBeInstanceOf(Date)
    expect(call.end).toBeInstanceOf(Date)
  })

  it('calls onChange with correct duration for preset', () => {
    render(<UnifiedTimePicker value={baseRange} onChange={onChange} />)
    fireEvent.click(screen.getByText('15m'))
    const { start, end } = onChange.mock.calls[0][0]
    const diffMinutes = Math.round((end.getTime() - start.getTime()) / 60_000)
    expect(diffMinutes).toBe(15)
  })

  it('calls onChange when start datetime input changes', () => {
    const { container } = render(<UnifiedTimePicker value={baseRange} onChange={onChange} />)
    const inputs = container.querySelectorAll('input[type="datetime-local"]')
    fireEvent.change(inputs[0], { target: { value: '2026-02-28T10:00' } })
    expect(onChange).toHaveBeenCalledTimes(1)
  })
})
