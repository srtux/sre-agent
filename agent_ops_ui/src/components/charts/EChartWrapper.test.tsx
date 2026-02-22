import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import EChartWrapper from './EChartWrapper'

// Mock echarts-for-react to avoid actual chart rendering in JSDOM.
// The real component accepts a ref, but our mock ignores it (ref warning is harmless in tests).
vi.mock('echarts-for-react', () => ({
  default: function MockReactECharts(
    props: { option: { series?: unknown[] }; style?: React.CSSProperties },
  ) {
    const seriesCount = Array.isArray(props.option?.series)
      ? props.option.series.length
      : 0
    return (
      <div
        data-testid="echarts-instance"
        style={props.style}
        data-series-count={seriesCount}
      >
        ECharts Mock
      </div>
    )
  },
}))

describe('EChartWrapper', () => {
  it('renders with default height', () => {
    const { container } = render(
      <EChartWrapper
        option={{
          series: [{ type: 'line', data: [1, 2, 3] }],
        }}
      />,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.style.height).toBe('300px')
  })

  it('renders with custom height as number', () => {
    const { container } = render(
      <EChartWrapper
        option={{ series: [{ type: 'line', data: [1] }] }}
        height={400}
      />,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.style.height).toBe('400px')
  })

  it('renders with custom height as string', () => {
    const { container } = render(
      <EChartWrapper
        option={{ series: [{ type: 'line', data: [1] }] }}
        height="50vh"
      />,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.style.height).toBe('50vh')
  })

  it('shows loading overlay when loading is true', () => {
    const { container } = render(
      <EChartWrapper
        option={{ series: [{ type: 'line', data: [1] }] }}
        loading={true}
      />,
    )
    // Loading overlay uses a spinner div
    const spinner = container.querySelector('[style*="animation"]')
    expect(spinner).toBeTruthy()
  })

  it('shows "No data available" when series is empty', () => {
    render(<EChartWrapper option={{ series: [] }} />)
    expect(screen.getByText('No data available')).toBeInTheDocument()
  })

  it('shows "No data available" when all series have empty data', () => {
    render(
      <EChartWrapper
        option={{ series: [{ type: 'line', data: [] }] }}
      />,
    )
    expect(screen.getByText('No data available')).toBeInTheDocument()
  })

  it('renders chart instance when data is provided', () => {
    render(
      <EChartWrapper
        option={{ series: [{ type: 'line', data: [1, 2, 3] }] }}
      />,
    )
    expect(screen.getByTestId('echarts-instance')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <EChartWrapper
        option={{ series: [{ type: 'line', data: [1] }] }}
        className="my-chart"
      />,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toBe('my-chart')
  })

  it('applies custom style prop', () => {
    const { container } = render(
      <EChartWrapper
        option={{ series: [{ type: 'line', data: [1] }] }}
        style={{ border: '1px solid red' }}
      />,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.style.border).toBe('1px solid red')
  })
})
