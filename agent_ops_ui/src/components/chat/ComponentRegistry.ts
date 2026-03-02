/**
 * Registry of A2UI component names → React components.
 * Maps x-sre-* component names from the backend to renderers.
 * Placeholder implementations display the component name and data summary.
 */
import React from 'react'

type SurfaceComponent = React.ComponentType<{ data: Record<string, unknown> }>

/**
 * Create a simple placeholder component that displays component name and data keys.
 */
function placeholder(displayName: string): SurfaceComponent {
  const Comp: SurfaceComponent = ({ data }) => {
    const keys = Object.keys(data)
    return React.createElement(
      'div',
      {
        style: {
          padding: '8px 12px',
          background: 'rgba(15, 23, 42, 0.5)',
          borderRadius: 8,
          border: '1px solid rgba(51, 65, 85, 0.5)',
          fontSize: 12,
          color: '#B0BEC5',
          fontFamily: "'JetBrains Mono', monospace",
        },
      },
      React.createElement(
        'div',
        { style: { color: '#06B6D4', fontWeight: 600, marginBottom: 4 } },
        displayName,
      ),
      React.createElement(
        'div',
        null,
        keys.length > 0
          ? `Keys: ${keys.join(', ')}`
          : 'No data',
      ),
    )
  }
  Comp.displayName = displayName
  return Comp
}

/** All registered A2UI component mappings. */
export const REGISTERED_COMPONENTS: Map<string, SurfaceComponent> = new Map([
  ['x-sre-trace-waterfall', placeholder('Trace Waterfall')],
  ['x-sre-log-entries', placeholder('Log Entries')],
  ['x-sre-log-patterns', placeholder('Log Patterns')],
  ['x-sre-metrics-chart', placeholder('Metrics Chart')],
  ['x-sre-metrics-dashboard', placeholder('Metrics Dashboard')],
  ['x-sre-incident-timeline', placeholder('Incident Timeline')],
  ['x-sre-council-synthesis', placeholder('Council Synthesis')],
  ['x-sre-agent-activity', placeholder('Agent Activity')],
  ['x-sre-agent-trace', placeholder('Agent Trace')],
  ['x-sre-agent-graph', placeholder('Agent Graph')],
  ['x-sre-service-topology', placeholder('Service Topology')],
  ['x-sre-remediation-plan', placeholder('Remediation Plan')],
  ['x-sre-vega-chart', placeholder('Vega Chart')],
  ['x-sre-slo-burn-rate', placeholder('SLO Burn Rate')],
  ['x-sre-postmortem', placeholder('Postmortem')],
  ['x-sre-alert-summary', placeholder('Alert Summary')],
])

/**
 * Look up a registered component by name.
 * Returns null if no component is registered for the given name.
 */
export function getComponent(name: string): SurfaceComponent | null {
  return REGISTERED_COMPONENTS.get(name) ?? null
}
