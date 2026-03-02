import { useRef, useEffect, useState, useCallback } from 'react'
import * as d3 from 'd3'
import type { AgentActivityData, AgentNodeType } from '../../types/sre'
import { colors, typography, spacing } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'
import { createForceSimulation, type ForceNode } from '../../utils/d3/forceLayout'

const NODE_COLORS: Record<AgentNodeType, string> = {
  coordinator: colors.primary,
  sub_agent: colors.cyan,
  tool: colors.warning,
  data_source: colors.blue,
}

const NODE_RADIUS = 20

// Inject pulse keyframes
const PULSE_KEYFRAME_ID = '__agent-activity-pulse'
if (typeof document !== 'undefined' && !document.getElementById(PULSE_KEYFRAME_ID)) {
  const style = document.createElement('style')
  style.id = PULSE_KEYFRAME_ID
  style.textContent = `
    @keyframes agentPulse {
      0%, 100% { r: ${NODE_RADIUS}; opacity: 1; }
      50% { r: ${NODE_RADIUS + 4}; opacity: 0.7; }
    }
  `
  document.head.appendChild(style)
}

interface GNode extends ForceNode {
  id: string
  name: string
  type: AgentNodeType
  isActive: boolean
}

export default function AgentActivityGraph({ data }: { data: AgentActivityData }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [dimensions, setDimensions] = useState({ width: 500, height: 350 })
  const containerRef = useRef<HTMLDivElement>(null)

  const measure = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect()
      setDimensions({ width: rect.width || 500, height: Math.max(rect.height, 350) })
    }
  }, [])

  useEffect(() => {
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [measure])

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const { width, height } = dimensions

    const gNodes: GNode[] = data.nodes.map((n) => ({
      id: n.id,
      name: n.name,
      type: n.type,
      isActive: n.status === 'active',
    }))

    const links = data.nodes.flatMap((n) =>
      n.connections.map((targetId) => ({ source: n.id, target: targetId })),
    )

    const sim = createForceSimulation(gNodes, links, width, height)

    // Edges
    const link = svg
      .append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', colors.surfaceBorder)
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.6)

    // Curved links
    link.attr('marker-end', '')

    // Nodes
    const node = svg
      .append('g')
      .selectAll<SVGCircleElement, GNode>('circle')
      .data(gNodes)
      .join('circle')
      .attr('r', NODE_RADIUS)
      .attr('fill', (d) => NODE_COLORS[d.type])
      .attr('stroke', (d) => (d.isActive ? '#fff' : 'none'))
      .attr('stroke-width', 2)
      .style('animation', (d) => (d.isActive ? 'agentPulse 1.5s ease-in-out infinite' : 'none'))
      .style('cursor', 'pointer')

    // Labels
    const label = svg
      .append('g')
      .selectAll<SVGTextElement, GNode>('text')
      .data(gNodes)
      .join('text')
      .text((d) => d.name)
      .attr('font-size', '11px')
      .attr('font-family', typography.monoFamily)
      .attr('fill', colors.textSecondary)
      .attr('text-anchor', 'middle')
      .attr('dy', NODE_RADIUS + 14)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const getX = (node: any): number => (node as GNode).x ?? 0
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const getY = (node: any): number => (node as GNode).y ?? 0

    sim.on('tick', () => {
      link
        .attr('x1', (d) => getX(d.source))
        .attr('y1', (d) => getY(d.source))
        .attr('x2', (d) => getX(d.target))
        .attr('y2', (d) => getY(d.target))

      node.attr('cx', (d) => d.x ?? 0).attr('cy', (d) => d.y ?? 0)
      label.attr('x', (d) => d.x ?? 0).attr('y', (d) => d.y ?? 0)
    })

    // Drag behavior
    node.call(
      d3
        .drag<SVGCircleElement, GNode>()
        .on('start', (event, d) => {
          if (!event.active) sim.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active) sim.alphaTarget(0)
          d.fx = null
          d.fy = null
        }),
    )

    return () => { sim.stop() }
  }, [data, dimensions])

  return (
    <div ref={containerRef} style={{ ...glassCard(), minHeight: 350, position: 'relative' }}>
      {data.phase && (
        <div style={{ position: 'absolute', top: spacing.sm, left: spacing.md, fontSize: typography.sizes.xs, color: colors.textMuted, fontFamily: typography.monoFamily }}>
          Phase: {data.phase}
        </div>
      )}
      <svg ref={svgRef} width={dimensions.width} height={dimensions.height} />
      {/* Legend */}
      <div style={{ position: 'absolute', bottom: spacing.sm, right: spacing.md, display: 'flex', gap: spacing.md, fontSize: typography.sizes.xs }}>
        {(Object.entries(NODE_COLORS) as [AgentNodeType, string][]).map(([type, color]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block' }} />
            <span style={{ color: colors.textMuted }}>{type.replace('_', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
