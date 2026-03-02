import * as d3 from 'd3'

export interface ForceNode extends d3.SimulationNodeDatum {
  id: string
}

export interface ForceLink {
  source: string
  target: string
}

/**
 * Create a D3 force simulation configured for graph layouts.
 */
export function createForceSimulation<N extends ForceNode>(
  nodes: N[],
  links: ForceLink[],
  width: number,
  height: number,
): d3.Simulation<N, d3.SimulationLinkDatum<N>> {
  return d3
    .forceSimulation(nodes)
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('charge', d3.forceManyBody().strength(-300))
    .force(
      'link',
      d3
        .forceLink<N, d3.SimulationLinkDatum<N>>(links as unknown as d3.SimulationLinkDatum<N>[])
        .id((d) => d.id)
        .distance(100),
    )
    .force('collide', d3.forceCollide(40))
}
