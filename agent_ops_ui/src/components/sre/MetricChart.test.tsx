import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import MetricChart from './MetricChart'
import { mockMetricSeries } from '../../test-utils/mockData'

// Mock EChartWrapper to render the option title and subtext so we can verify them
vi.mock('../charts/EChartWrapper', () => ({
  default: ({ option }: { option: { title?: { text?: string; subtext?: string } } }) => (
    <div data-testid="echart">
      {option.title?.text && <span>{option.title.text}</span>}
      {option.title?.subtext && <span>{option.title.subtext}</span>}
    </div>
  ),
}))

describe('MetricChart', () => {
  it('renders metric name', () => {
    render(<MetricChart data={mockMetricSeries} />)
    expect(screen.getByText(/request_latency_ms/)).toBeDefined()
  })

  it('renders chart component', () => {
    render(<MetricChart data={mockMetricSeries} />)
    expect(screen.getByTestId('echart')).toBeDefined()
  })

  it('renders unit label when provided', () => {
    render(<MetricChart data={mockMetricSeries} />)
    // The component sets option.title.subtext = "Unit: ms"
    expect(screen.getByText(/Unit: ms/)).toBeDefined()
  })
})
