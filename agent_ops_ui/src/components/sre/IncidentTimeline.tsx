import { useRef, useEffect, useState, useCallback } from 'react'
import * as d3 from 'd3'
import type { IncidentTimelineData, TimelineEventType } from '../../types/sre'
import { colors, typography, spacing, radii } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'
import { calculateTimelinePositions } from '../../utils/d3/timelineLayout'

const EVENT_COLORS: Record<TimelineEventType, string> = {
  alert: colors.error,
  deployment: colors.blue,
  config_change: colors.purple,
  scaling: colors.cyan,
  incident: colors.critical,
  recovery: colors.success,
  agent_action: colors.primary,
}

const SEV_BADGE: Record<string, { bg: string; text: string }> = {
  critical: { bg: `${colors.critical}25`, text: colors.critical },
  high: { bg: `${colors.error}25`, text: colors.error },
  medium: { bg: `${colors.warning}25`, text: colors.warning },
  low: { bg: `${colors.info}25`, text: colors.info },
  info: { bg: `${colors.severityInfo}25`, text: colors.severityInfo },
}

export default function IncidentTimeline({ data }: { data: IncidentTimelineData }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [height, setHeight] = useState(400)

  const measure = useCallback(() => {
    // Height based on event count
    setHeight(Math.max(data.events.length * 80 + 80, 300))
  }, [data.events.length])

  useEffect(() => { measure() }, [measure])

  useEffect(() => {
    if (!svgRef.current || !data.events.length) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const TIMELINE_X = 60
    const CARD_X = 90
    const CARD_W = 300

    const positioned = calculateTimelinePositions(data.events, height, 40)

    // Vertical timeline line
    svg
      .append('line')
      .attr('x1', TIMELINE_X)
      .attr('y1', 30)
      .attr('x2', TIMELINE_X)
      .attr('y2', height - 30)
      .attr('stroke', colors.surfaceBorder)
      .attr('stroke-width', 2)

    // Events
    const g = svg.append('g')

    for (const { item: event, y } of positioned) {
      const color = EVENT_COLORS[event.type] ?? colors.textMuted
      const sev = SEV_BADGE[event.severity] ?? SEV_BADGE.info

      // Circle on timeline
      g.append('circle')
        .attr('cx', TIMELINE_X)
        .attr('cy', y)
        .attr('r', 8)
        .attr('fill', color)
        .attr('stroke', colors.surface)
        .attr('stroke-width', 2)

      // Connector line
      g.append('line')
        .attr('x1', TIMELINE_X + 8)
        .attr('y1', y)
        .attr('x2', CARD_X)
        .attr('y2', y)
        .attr('stroke', colors.surfaceBorder)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '3 2')

      // Card background
      g.append('rect')
        .attr('x', CARD_X)
        .attr('y', y - 24)
        .attr('width', CARD_W)
        .attr('height', 48)
        .attr('rx', radii.md)
        .attr('fill', colors.surface)
        .attr('stroke', colors.surfaceBorder)
        .attr('stroke-width', 1)

      // Title
      g.append('text')
        .attr('x', CARD_X + 10)
        .attr('y', y - 6)
        .attr('fill', colors.textPrimary)
        .attr('font-size', '12px')
        .attr('font-family', typography.fontFamily)
        .attr('font-weight', 600)
        .text(event.title.length > 40 ? event.title.slice(0, 37) + '...' : event.title)

      // Description
      if (event.description) {
        g.append('text')
          .attr('x', CARD_X + 10)
          .attr('y', y + 12)
          .attr('fill', colors.textMuted)
          .attr('font-size', '10px')
          .attr('font-family', typography.monoFamily)
          .text(
            event.description.length > 50
              ? event.description.slice(0, 47) + '...'
              : event.description,
          )
      }

      // Severity badge
      g.append('rect')
        .attr('x', CARD_X + CARD_W - 60)
        .attr('y', y - 20)
        .attr('width', 50)
        .attr('height', 16)
        .attr('rx', 8)
        .attr('fill', sev.bg)

      g.append('text')
        .attr('x', CARD_X + CARD_W - 35)
        .attr('y', y - 9)
        .attr('fill', sev.text)
        .attr('font-size', '9px')
        .attr('font-weight', 600)
        .attr('text-anchor', 'middle')
        .text(event.severity.toUpperCase())

      // Timestamp on the left
      g.append('text')
        .attr('x', TIMELINE_X - 14)
        .attr('y', y + 4)
        .attr('fill', colors.textMuted)
        .attr('font-size', '9px')
        .attr('font-family', typography.monoFamily)
        .attr('text-anchor', 'end')
        .text(new Date(event.timestamp).toLocaleTimeString())
    }
  }, [data, height])

  if (!data.events.length) {
    return (
      <div style={{ ...glassCard(), padding: spacing.lg, color: colors.textMuted, textAlign: 'center' }}>
        No timeline events
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ ...glassCard(), overflow: 'auto' }}>
      {/* Header */}
      <div style={{ padding: `${spacing.sm}px ${spacing.md}px`, borderBottom: `1px solid ${colors.surfaceBorder}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: typography.sizes.md, fontWeight: 600, color: colors.textPrimary }}>
          {data.title}
        </span>
        <span style={{ fontSize: typography.sizes.xs, color: colors.textMuted }}>
          {data.serviceName} &middot; {data.status}
        </span>
      </div>
      <svg ref={svgRef} width={420} height={height} />
    </div>
  )
}
