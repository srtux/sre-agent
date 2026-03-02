import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MetricsDashboard from './MetricsDashboard'
import { mockMetricsDashboard } from '../../test-utils/mockData'

describe('MetricsDashboard', () => {
  it('renders all metric cards', () => {
    render(<MetricsDashboard data={mockMetricsDashboard} />)
    expect(screen.getByText('Request Rate')).toBeDefined()
    expect(screen.getByText('Error Rate')).toBeDefined()
    expect(screen.getByText('P99 Latency')).toBeDefined()
    expect(screen.getByText('CPU Usage')).toBeDefined()
  })

  it('shows metric values', () => {
    render(<MetricsDashboard data={mockMetricsDashboard} />)
    // currentValue is rendered via .toLocaleString(), so 1250 may be "1,250"
    // Use a regex that matches either "1250" or "1,250"
    expect(screen.getByText(/1,?250/)).toBeDefined()
    expect(screen.getByText('2.5')).toBeDefined()
  })

  it('shows anomaly description for critical metrics', () => {
    render(<MetricsDashboard data={mockMetricsDashboard} />)
    // The Error Rate metric has anomalyDescription: "Spike in 5xx errors"
    expect(screen.getByText(/Spike in 5xx errors/)).toBeDefined()
  })
})
