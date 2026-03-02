/**
 * Live trace panel — displays traces collected during investigation.
 * Expandable span list with Cloud Trace deep link.
 */
import { useState, useMemo } from 'react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import DashboardCardWrapper from '../../common/DashboardCardWrapper'
import { colors, typography, spacing } from '../../../theme/tokens'
import type { SpanInfo } from '../../../types/sre'

function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}μs`
  if (ms < 1000) return `${ms.toFixed(1)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function spanDurationMs(span: SpanInfo): number {
  if (span.duration != null) return span.duration
  const start = new Date(span.startTime).getTime()
  const end = new Date(span.endTime).getTime()
  return end - start
}

const styles: Record<string, React.CSSProperties> = {
  spanTable: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    marginTop: spacing.sm,
  },
  th: {
    textAlign: 'left' as const,
    padding: `${spacing.xs}px ${spacing.sm}px`,
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    borderBottom: `1px solid ${colors.surfaceBorder}`,
    fontWeight: typography.weights.medium,
  },
  td: {
    padding: `${spacing.xs}px ${spacing.sm}px`,
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    borderBottom: `1px solid rgba(51, 65, 85, 0.3)`,
  },
  traceId: {
    fontFamily: typography.monoFamily,
    fontSize: typography.sizes.sm,
    color: colors.cyan,
  },
  stat: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginRight: spacing.lg,
  },
  statValue: {
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
  },
  expandBtn: {
    background: 'transparent',
    border: 'none',
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    padding: `${spacing.xs}px 0`,
  },
  link: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    color: colors.cyan,
    fontSize: typography.sizes.xs,
    textDecoration: 'none',
    marginTop: spacing.sm,
  },
  statusDot: {
    display: 'inline-block',
    width: 6,
    height: 6,
    borderRadius: '50%',
    marginRight: 4,
  },
}

function statusColor(status: string): string {
  if (status === 'OK' || status === 'UNSET') return colors.success
  if (status === 'ERROR') return colors.error
  return colors.warning
}

function TraceCard({ item }: { item: ReturnType<ReturnType<typeof useDashboardStore.getState>['itemsOfType']>[number] }) {
  const [expanded, setExpanded] = useState(false)
  const removeItem = useDashboardStore((s) => s.removeItem)
  const trace = item.trace
  if (!trace) return null

  const spanCount = trace.spans.length
  const totalDuration = trace.spans.reduce((max, s) => {
    const d = spanDurationMs(s)
    return d > max ? d : max
  }, 0)

  const traceIdShort = trace.traceId.slice(0, 16)

  return (
    <DashboardCardWrapper
      title={`Trace ${traceIdShort}`}
      subtitle={`${spanCount} spans`}
      timestamp={item.timestamp}
      onRemove={() => removeItem(item.id)}
    >
      <div style={{ display: 'flex', gap: spacing.lg, marginBottom: spacing.sm }}>
        <span style={styles.stat}>
          Spans: <span style={styles.statValue}>{spanCount}</span>
        </span>
        <span style={styles.stat}>
          Duration: <span style={styles.statValue}>{formatDuration(totalDuration)}</span>
        </span>
      </div>

      <button style={styles.expandBtn} onClick={() => setExpanded((p) => !p)}>
        {expanded ? '▲ Hide spans' : '▼ Show spans'}
      </button>

      {expanded && (
        <table style={styles.spanTable}>
          <thead>
            <tr>
              <th style={styles.th}>Name</th>
              <th style={styles.th}>Duration</th>
              <th style={styles.th}>Status</th>
            </tr>
          </thead>
          <tbody>
            {trace.spans.map((span) => (
              <tr key={span.spanId}>
                <td style={{ ...styles.td, fontFamily: typography.monoFamily, fontSize: typography.sizes.xs }}>
                  {span.name}
                </td>
                <td style={styles.td}>{formatDuration(spanDurationMs(span))}</td>
                <td style={styles.td}>
                  <span style={{ ...styles.statusDot, background: statusColor(span.status) }} />
                  {span.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <a
        style={styles.link}
        href={`https://console.cloud.google.com/traces/list?tid=${trace.traceId}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        Open in Cloud Trace ↗
      </a>
    </DashboardCardWrapper>
  )
}

export default function LiveTracePanel() {
  const allItems = useDashboardStore((s) => s.items)
  const items = useMemo(() => allItems.filter((i) => i.type === 'traces'), [allItems])

  return (
    <div>
      {items.map((item) => (
        <TraceCard key={item.id} item={item} />
      ))}
    </div>
  )
}
