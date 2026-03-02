import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TraceWaterfall from './TraceWaterfall'
import { mockTrace } from '../../test-utils/mockData'

describe('TraceWaterfall', () => {
  it('renders trace ID (truncated)', () => {
    render(<TraceWaterfall data={mockTrace} />)
    // Component renders: Trace {traceId.slice(0,8)}... => "Trace trace-ab..."
    expect(screen.getByText(/Trace trace-ab/)).toBeDefined()
  })

  it('renders span names', () => {
    render(<TraceWaterfall data={mockTrace} />)
    expect(screen.getByText(/HTTP GET/)).toBeDefined()
    expect(screen.getByText(/DB Query/)).toBeDefined()
  })

  it('renders duration bars', () => {
    const { container } = render(<TraceWaterfall data={mockTrace} />)
    // Should have visual bars for each span
    expect(container.querySelectorAll('[style]').length).toBeGreaterThan(0)
  })
})
