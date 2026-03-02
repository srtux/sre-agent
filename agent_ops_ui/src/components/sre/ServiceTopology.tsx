import { useRef, useEffect, useState, useCallback } from 'react'
import * as d3 from 'd3'
import type { ServiceTopologyData, ServiceHealth } from '../../types/sre'
import { colors, typography, spacing } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'
import { createForceSimulation, type ForceNode } from '../../utils/d3/forceLayout'

const HEALTH_COLORS: Record<ServiceHealth, string> = {
  healthy: colors.success,
  degraded: colors.warning,
  unhealthy: colors.error,
}

interface SNode extends ForceNode {
  id: string
  name: string
  health: ServiceHealth
  radius: number
  isSource: boolean
}

export default function ServiceTopology({ data }: { data: ServiceTopologyData }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 500, height: 400 })

  const measure = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect()
      setDimensions({ width: rect.width || 500, height: Math.max(rect.height, 400) })
    }
  }, [])

  useEffect(() => {
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [measure])

  useEffect(() => {
    if (!svgRef.current || !data.services.length) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const { width, height } = dimensions

    // Scale radius by requestsPerSec
    const maxRps = Math.max(...data.services.map((s) => s.requestsPerSec ?? 1), 1)

    const affectedSet = new Set(data.affectedPath ?? [])

    const nodes: SNode[] = data.services.map((s) => ({
      id: s.id,
      name: s.name,
      health: s.health,
      radius: 12 + ((s.requestsPerSec ?? 0) / maxRps) * 18,
      isSource: s.isIncidentSource ?? false,
    }))

    const links = data.connections.map((c) => ({
      source: c.source,
      target: c.target,
    }))

    const connMap = new Map(data.connections.map((c) => [`${c.source}->${c.target}`, c]))
    const maxLatency = Math.max(...data.connections.map((c) => c.latency ?? 1), 1)

    const sim = createForceSimulation(nodes, links, width, height)

    // Edges
    const link = svg
      .append('g')
      .selectAll<SVGLineElement, (typeof links)[number]>('line')
      .data(links)
      .join('line')
      .attr('stroke', (_d, i) => {
        const key = `${String(links[i].source)}->${String(links[i].target)}`
        return connMap.get(key)?.isAffectedPath ? colors.error : colors.surfaceBorder
      })
      .attr('stroke-width', (_d, i) => {
        const key = `${String(links[i].source)}->${String(links[i].target)}`
        const conn = connMap.get(key)
        return 1 + ((conn?.latency ?? 0) / maxLatency) * 3
      })
      .attr('stroke-dasharray', (_d, i) => {
        const key = `${String(links[i].source)}->${String(links[i].target)}`
        return connMap.get(key)?.isAffectedPath ? '6 3' : 'none'
      })
      .attr('stroke-opacity', 0.7)

    // Nodes
    const node = svg
      .append('g')
      .selectAll<SVGCircleElement, SNode>('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => d.radius)
      .attr('fill', (d) => HEALTH_COLORS[d.health])
      .attr('stroke', (d) => {
        if (d.isSource) return colors.error
        if (affectedSet.has(d.id)) return colors.warning
        return 'none'
      })
      .attr('stroke-width', (d) => (d.isSource || affectedSet.has(d.id) ? 3 : 0))
      .style('cursor', 'pointer')

    // Labels
    const label = svg
      .append('g')
      .selectAll<SVGTextElement, SNode>('text')
      .data(nodes)
      .join('text')
      .text((d) => d.name)
      .attr('font-size', '11px')
      .attr('font-family', typography.monoFamily)
      .attr('fill', colors.textSecondary)
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => d.radius + 14)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const getX = (node: any): number => (node as SNode).x ?? 0
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const getY = (node: any): number => (node as SNode).y ?? 0

    sim.on('tick', () => {
      link
        .attr('x1', (d) => getX(d.source))
        .attr('y1', (d) => getY(d.source))
        .attr('x2', (d) => getX(d.target))
        .attr('y2', (d) => getY(d.target))

      node.attr('cx', (d) => d.x ?? 0).attr('cy', (d) => d.y ?? 0)
      label.attr('x', (d) => d.x ?? 0).attr('y', (d) => d.y ?? 0)
    })

    // Drag
    node.call(
      d3
        .drag<SVGCircleElement, SNode>()
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
    <div ref={containerRef} style={{ ...glassCard(), minHeight: 400, position: 'relative' }}>
      <svg ref={svgRef} width={dimensions.width} height={dimensions.height} />
      {/* Legend */}
      <div style={{ position: 'absolute', bottom: spacing.sm, right: spacing.md, display: 'flex', gap: spacing.md, fontSize: typography.sizes.xs }}>
        {(Object.entries(HEALTH_COLORS) as [ServiceHealth, string][]).map(([h, c]) => (
          <div key={h} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, display: 'inline-block' }} />
            <span style={{ color: colors.textMuted }}>{h}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
