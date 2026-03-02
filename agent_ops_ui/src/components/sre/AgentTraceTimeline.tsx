import { useRef, useEffect, useState, useCallback } from 'react'
import * as d3 from 'd3'
import type { AgentTraceData, AgentTraceKind } from '../../types/sre'
import { colors, typography, spacing } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

const KIND_COLORS: Record<AgentTraceKind, string> = {
  agent_invocation: colors.agentInvocation,
  llm_call: colors.llmCall,
  tool_execution: colors.toolExecution,
  sub_agent_delegation: colors.subAgentDelegation,
}

const BAR_HEIGHT = 22
const ROW_GAP = 4
const LABEL_WIDTH = 140
const MARGIN = { top: 30, right: 20, bottom: 30, left: LABEL_WIDTH + 10 }

export default function AgentTraceTimeline({ data }: { data: AgentTraceData }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(700)

  const measure = useCallback(() => {
    if (containerRef.current) {
      const w = containerRef.current.getBoundingClientRect().width
      setWidth(w || 700)
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

    const nodes = [...data.nodes].sort((a, b) => a.startOffsetMs - b.startOffsetMs)

    const chartWidth = width - MARGIN.left - MARGIN.right
    const chartHeight = nodes.length * (BAR_HEIGHT + ROW_GAP)
    const totalHeight = chartHeight + MARGIN.top + MARGIN.bottom

    svg.attr('height', totalHeight)

    const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`)

    // X scale: time offset
    const xScale = d3
      .scaleLinear()
      .domain([0, data.totalDurationMs])
      .range([0, chartWidth])

    // X axis
    g.append('g')
      .attr('transform', `translate(0,${chartHeight})`)
      .call(
        d3
          .axisBottom(xScale)
          .ticks(6)
          .tickFormat((d) => {
            const ms = d as number
            return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
          }),
      )
      .selectAll('text')
      .attr('fill', colors.textMuted)
      .attr('font-size', '10px')

    g.selectAll('.domain').attr('stroke', colors.surfaceBorder)
    g.selectAll('.tick line').attr('stroke', colors.surfaceBorder)

    // Bars
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i]
      const y = i * (BAR_HEIGHT + ROW_GAP)
      const x = xScale(node.startOffsetMs)
      const barWidth = Math.max(xScale(node.durationMs) - xScale(0), 2)

      // Label
      g.append('text')
        .attr('x', -8)
        .attr('y', y + BAR_HEIGHT / 2 + 4)
        .attr('fill', colors.textSecondary)
        .attr('font-size', '10px')
        .attr('font-family', typography.monoFamily)
        .attr('text-anchor', 'end')
        .text(node.name.length > 20 ? node.name.slice(0, 17) + '...' : node.name)

      // Bar
      g.append('rect')
        .attr('x', x)
        .attr('y', y)
        .attr('width', barWidth)
        .attr('height', BAR_HEIGHT)
        .attr('rx', 3)
        .attr('fill', KIND_COLORS[node.kind])
        .attr('opacity', node.hasError ? 0.9 : 0.8)
        .attr('stroke', node.hasError ? colors.error : 'none')
        .attr('stroke-width', node.hasError ? 2 : 0)

      // Token count on bar (if it fits)
      const tokens = (node.inputTokens ?? 0) + (node.outputTokens ?? 0)
      if (tokens > 0 && barWidth > 40) {
        g.append('text')
          .attr('x', x + barWidth / 2)
          .attr('y', y + BAR_HEIGHT / 2 + 3)
          .attr('fill', '#fff')
          .attr('font-size', '9px')
          .attr('font-family', typography.monoFamily)
          .attr('text-anchor', 'middle')
          .attr('font-weight', 600)
          .text(`${tokens >= 1000 ? (tokens / 1000).toFixed(1) + 'K' : tokens} tok`)
      }

      // Duration label after bar
      g.append('text')
        .attr('x', x + barWidth + 4)
        .attr('y', y + BAR_HEIGHT / 2 + 3)
        .attr('fill', colors.textMuted)
        .attr('font-size', '9px')
        .attr('font-family', typography.monoFamily)
        .text(node.durationMs >= 1000 ? `${(node.durationMs / 1000).toFixed(1)}s` : `${Math.round(node.durationMs)}ms`)
    }
  }, [data, width])

  if (!data.nodes.length) {
    return (
      <div style={{ ...glassCard(), padding: spacing.lg, color: colors.textMuted, textAlign: 'center' }}>
        No agent trace data
      </div>
    )
  }

  const svgHeight = data.nodes.length * (BAR_HEIGHT + ROW_GAP) + MARGIN.top + MARGIN.bottom

  return (
    <div ref={containerRef} style={{ ...glassCard(), overflow: 'auto' }}>
      {/* Summary header */}
      <div style={{ padding: `${spacing.sm}px ${spacing.md}px`, borderBottom: `1px solid ${colors.surfaceBorder}`, display: 'flex', gap: spacing.lg, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: typography.sizes.sm, color: colors.textSecondary }}>
          {data.rootAgentName}
        </span>
        <span style={{ fontSize: typography.sizes.xs, color: colors.textMuted, fontFamily: typography.monoFamily }}>
          {data.totalDurationMs >= 1000 ? `${(data.totalDurationMs / 1000).toFixed(1)}s` : `${data.totalDurationMs}ms`}
          {' \u00b7 '}
          {data.llmCallCount} LLM calls
          {' \u00b7 '}
          {data.toolCallCount} tool calls
          {' \u00b7 '}
          {((data.totalInputTokens + data.totalOutputTokens) / 1000).toFixed(1)}K tokens
        </span>
      </div>

      <svg ref={svgRef} width={width} height={svgHeight} />

      {/* Legend */}
      <div style={{ padding: `${spacing.sm}px ${spacing.md}px`, display: 'flex', gap: spacing.md, flexWrap: 'wrap', borderTop: `1px solid ${colors.surfaceBorder}` }}>
        {(Object.entries(KIND_COLORS) as [AgentTraceKind, string][]).map(([kind, color]) => (
          <div key={kind} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: typography.sizes.xs }}>
            <span style={{ width: 12, height: 8, borderRadius: 2, background: color, display: 'inline-block' }} />
            <span style={{ color: colors.textMuted }}>{kind.replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
