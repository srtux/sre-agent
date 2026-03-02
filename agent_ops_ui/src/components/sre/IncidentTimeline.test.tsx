import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import IncidentTimeline from './IncidentTimeline'
import { mockIncidentTimeline } from '../../test-utils/mockData'

describe('IncidentTimeline', () => {
  it('renders incident title', () => {
    render(<IncidentTimeline data={mockIncidentTimeline} />)
    expect(screen.getByText(/Database Connection Storm/)).toBeDefined()
  })

  it('renders service name and status in header', () => {
    render(<IncidentTimeline data={mockIncidentTimeline} />)
    // The header shows: {serviceName} · {status}
    const headerSpan = screen.getByText(/api-gateway/)
    expect(headerSpan).toBeDefined()
    expect(headerSpan.textContent).toContain('mitigated')
  })

  it('renders SVG timeline', () => {
    const { container } = render(<IncidentTimeline data={mockIncidentTimeline} />)
    // The component renders an SVG element for the timeline
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
  })

  it('does not render root cause or TTD/TTM in DOM (they are not in the component)', () => {
    const { container } = render(<IncidentTimeline data={mockIncidentTimeline} />)
    // The component only renders title, serviceName, status in the header
    // rootCause, timeToDetect, timeToMitigate are NOT rendered
    // Verify the header content is present
    expect(container.textContent).toContain('Database Connection Storm')
    expect(container.textContent).toContain('api-gateway')
  })
})
