import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ServiceTopology from './ServiceTopology'
import { mockServiceTopology } from '../../test-utils/mockData'

describe('ServiceTopology', () => {
  it('renders service names', () => {
    render(<ServiceTopology data={mockServiceTopology} />)
    expect(screen.getByText('api-gateway')).toBeDefined()
    expect(screen.getByText('auth-service')).toBeDefined()
    expect(screen.getByText('cloud-sql')).toBeDefined()
  })

  it('shows health status indicators', () => {
    render(<ServiceTopology data={mockServiceTopology} />)
    expect(screen.getByText(/degraded/i)).toBeDefined()
    expect(screen.getByText(/unhealthy/i)).toBeDefined()
  })

  it('renders connection lines', () => {
    const { container } = render(<ServiceTopology data={mockServiceTopology} />)
    // SVG lines or styled divs should exist for connections
    expect(container.querySelectorAll('[style]').length).toBeGreaterThan(0)
  })
})
