import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import A2UISurfaceRenderer from './A2UISurfaceRenderer'
import type { Surface } from '../../types/a2ui'

vi.mock('./ComponentRegistry', () => ({
  getComponent: (name: string) => {
    if (name === 'x-sre-trace-waterfall') {
      return ({ data }: { data: Record<string, unknown> }) => (
        <div data-testid="registered-comp">TraceWaterfall: {JSON.stringify(data)}</div>
      )
    }
    return null
  },
}))

vi.mock('../../types/a2ui', async () => {
  const actual = await vi.importActual('../../types/a2ui')
  return {
    ...actual,
    unwrapComponentData: (data: Record<string, unknown>) => data,
  }
})

describe('A2UISurfaceRenderer', () => {
  it('renders registered component with data', () => {
    const surface: Surface = {
      id: 's1',
      componentName: 'x-sre-trace-waterfall',
      data: { traceId: 't1' },
      status: 'complete',
    }
    render(<A2UISurfaceRenderer surface={surface} />)
    expect(screen.getByTestId('registered-comp')).toBeDefined()
    expect(screen.getByText(/t1/)).toBeDefined()
  })

  it('renders fallback for unknown component', () => {
    const surface: Surface = {
      id: 's2',
      componentName: 'x-sre-unknown',
      data: { key: 'value' },
      status: 'complete',
    }
    render(<A2UISurfaceRenderer surface={surface} />)
    // Fallback renders component name or JSON
    const container = document.body
    expect(container.textContent).toBeTruthy()
  })
})
