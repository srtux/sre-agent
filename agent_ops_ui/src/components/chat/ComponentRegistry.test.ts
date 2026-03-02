import { describe, it, expect } from 'vitest'
import { getComponent, REGISTERED_COMPONENTS } from './ComponentRegistry'

describe('ComponentRegistry', () => {
  it('has all expected x-sre-* component names registered', () => {
    const expected = [
      'x-sre-trace-waterfall',
      'x-sre-log-entries',
      'x-sre-log-patterns',
      'x-sre-metrics-chart',
      'x-sre-metrics-dashboard',
      'x-sre-incident-timeline',
      'x-sre-council-synthesis',
      'x-sre-agent-activity',
      'x-sre-agent-trace',
      'x-sre-agent-graph',
      'x-sre-service-topology',
      'x-sre-remediation-plan',
      'x-sre-vega-chart',
      'x-sre-slo-burn-rate',
      'x-sre-postmortem',
      'x-sre-alert-summary',
    ]
    for (const name of expected) {
      expect(REGISTERED_COMPONENTS.has(name)).toBe(true)
    }
  })

  it('getComponent returns a component for registered names', () => {
    const comp = getComponent('x-sre-trace-waterfall')
    expect(comp).not.toBeNull()
    expect(typeof comp).toBe('function')
  })

  it('getComponent returns null for unknown names', () => {
    expect(getComponent('x-sre-nonexistent')).toBeNull()
  })

  it('registered components are callable React components', () => {
    const comp = getComponent('x-sre-log-entries')
    expect(comp).not.toBeNull()
    // Each component accepts { data } prop
    expect(typeof comp).toBe('function')
  })
})
