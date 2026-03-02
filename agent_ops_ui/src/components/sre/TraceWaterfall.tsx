import { useState, useMemo } from 'react'
import type { Trace, SpanInfo } from '../../types/sre'
import { colors, typography, spacing, radii } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

interface SpanRow {
  span: SpanInfo
  depth: number
  leftPct: number
  widthPct: number
}

function buildRows(spans: SpanInfo[], traceStart: number, totalDuration: number): SpanRow[] {
  const parentMap = new Map<string, string | null>()
  const childMap = new Map<string, SpanInfo[]>()

  for (const s of spans) {
    parentMap.set(s.spanId, s.parentSpanId ?? null)
    const pid = s.parentSpanId ?? '__root__'
    if (!childMap.has(pid)) childMap.set(pid, [])
    childMap.get(pid)!.push(s)
  }

  const depthOf = (id: string): number => {
    let d = 0
    let cur = parentMap.get(id) ?? null
    while (cur) {
      d++
      cur = parentMap.get(cur) ?? null
    }
    return d
  }

  const rows: SpanRow[] = []

  function walk(parentId: string) {
    const children = childMap.get(parentId) ?? []
    children.sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())
    for (const span of children) {
      const start = new Date(span.startTime).getTime()
      const end = new Date(span.endTime).getTime()
      const dur = end - start
      const leftPct = totalDuration > 0 ? ((start - traceStart) / totalDuration) * 100 : 0
      const widthPct = totalDuration > 0 ? Math.max((dur / totalDuration) * 100, 0.5) : 100
      rows.push({ span, depth: depthOf(span.spanId), leftPct, widthPct })
      walk(span.spanId)
    }
  }

  walk('__root__')

  // If no tree structure was found, just render flat
  if (rows.length === 0) {
    for (const span of spans) {
      const start = new Date(span.startTime).getTime()
      const end = new Date(span.endTime).getTime()
      const dur = end - start
      const leftPct = totalDuration > 0 ? ((start - traceStart) / totalDuration) * 100 : 0
      const widthPct = totalDuration > 0 ? Math.max((dur / totalDuration) * 100, 0.5) : 100
      rows.push({ span, depth: 0, leftPct, widthPct })
    }
  }

  return rows
}

function statusColor(status: string): string {
  const s = status.toLowerCase()
  if (s === 'error' || s === 'err') return colors.error
  if (s === 'unset') return colors.warning
  return colors.success
}

function formatDuration(span: SpanInfo): string {
  const start = new Date(span.startTime).getTime()
  const end = new Date(span.endTime).getTime()
  const ms = end - start
  if (ms < 1) return '<1ms'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export default function TraceWaterfall({ data }: { data: Trace }) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const { rows, totalDuration } = useMemo(() => {
    if (!data.spans.length) return { rows: [], totalDuration: 0 }
    const times = data.spans.flatMap((s) => [
      new Date(s.startTime).getTime(),
      new Date(s.endTime).getTime(),
    ])
    const traceStart = Math.min(...times)
    const traceEnd = Math.max(...times)
    const totalDuration = traceEnd - traceStart
    return { rows: buildRows(data.spans, traceStart, totalDuration), totalDuration }
  }, [data])

  if (!data.spans.length) {
    return (
      <div style={{ ...containerStyle, display: 'flex', alignItems: 'center', justifyContent: 'center', color: colors.textMuted }}>
        No spans
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <span style={{ fontSize: typography.sizes.sm, color: colors.textSecondary }}>
          Trace {data.traceId.slice(0, 8)}...
        </span>
        <span style={{ fontSize: typography.sizes.xs, color: colors.textMuted }}>
          {data.spans.length} spans &middot; {totalDuration.toFixed(0)}ms
        </span>
      </div>

      <div style={scrollStyle}>
        {rows.map((row) => {
          const isHovered = hoveredId === row.span.spanId
          return (
            <div
              key={row.span.spanId}
              style={{
                display: 'flex',
                alignItems: 'center',
                height: 28,
                paddingLeft: row.depth * 16 + spacing.sm,
                position: 'relative',
              }}
              onMouseEnter={() => setHoveredId(row.span.spanId)}
              onMouseLeave={() => setHoveredId(null)}
            >
              {/* Span name label */}
              <span
                style={{
                  width: 140,
                  minWidth: 140,
                  fontSize: typography.sizes.xs,
                  color: colors.textSecondary,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  fontFamily: typography.monoFamily,
                  flexShrink: 0,
                }}
              >
                {row.span.name}
              </span>

              {/* Bar area */}
              <div style={{ flex: 1, position: 'relative', height: 16, marginLeft: spacing.sm }}>
                <div
                  style={{
                    position: 'absolute',
                    left: `${row.leftPct}%`,
                    width: `${row.widthPct}%`,
                    height: '100%',
                    backgroundColor: statusColor(row.span.status),
                    borderRadius: radii.sm,
                    opacity: isHovered ? 1 : 0.75,
                    transition: 'opacity 0.15s ease',
                    minWidth: 2,
                  }}
                />
                {/* Duration label on bar */}
                <span
                  style={{
                    position: 'absolute',
                    left: `${row.leftPct + row.widthPct + 0.5}%`,
                    top: 1,
                    fontSize: '10px',
                    color: colors.textMuted,
                    whiteSpace: 'nowrap',
                    fontFamily: typography.monoFamily,
                  }}
                >
                  {formatDuration(row.span)}
                </span>
              </div>

              {/* Tooltip */}
              {isHovered && (
                <div style={tooltipStyle}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{row.span.name}</div>
                  <div>Duration: {formatDuration(row.span)}</div>
                  <div>Status: {row.span.status}</div>
                  {Object.keys(row.span.attributes).length > 0 && (
                    <div style={{ marginTop: 4, maxHeight: 100, overflow: 'auto' }}>
                      {Object.entries(row.span.attributes).slice(0, 5).map(([k, v]) => (
                        <div key={k} style={{ fontSize: '10px', color: colors.textMuted }}>
                          {k}: {String(v)}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const containerStyle: React.CSSProperties = {
  ...glassCard(),
  minHeight: 200,
  padding: spacing.md,
  overflow: 'hidden',
}

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: spacing.sm,
  paddingBottom: spacing.sm,
  borderBottom: `1px solid ${colors.surfaceBorder}`,
}

const scrollStyle: React.CSSProperties = {
  overflowY: 'auto',
  maxHeight: 400,
}

const tooltipStyle: React.CSSProperties = {
  position: 'absolute',
  right: 0,
  top: 30,
  zIndex: 100,
  background: colors.surface,
  border: `1px solid ${colors.surfaceBorder}`,
  borderRadius: radii.md,
  padding: spacing.sm,
  fontSize: typography.sizes.xs,
  color: colors.textPrimary,
  boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
  minWidth: 180,
  fontFamily: typography.monoFamily,
}
