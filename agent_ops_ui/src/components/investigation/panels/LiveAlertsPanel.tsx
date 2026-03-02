/**
 * Live alerts panel — shows incident timeline events sorted by severity.
 * Header with summary stat badges, followed by event cards.
 */
import { useMemo } from 'react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import { colors, typography, radii, spacing } from '../../../theme/tokens'
import { glassCard } from '../../../theme/glassStyles'
import type { TimelineEvent } from '../../../types/sre'

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: colors.severityCritical,
  high: colors.severityError,
  medium: colors.severityWarning,
  low: colors.severityInfo,
  info: colors.severityDebug,
}

const styles: Record<string, React.CSSProperties> = {
  summaryRow: {
    display: 'flex',
    gap: spacing.sm,
    marginBottom: spacing.lg,
    flexWrap: 'wrap' as const,
  },
  summaryBadge: {
    padding: `${spacing.xs}px ${spacing.md}px`,
    borderRadius: radii.round,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
  },
  eventCard: {
    ...glassCard(),
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  eventHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  eventTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.textPrimary,
    flex: 1,
  },
  eventTimestamp: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    fontFamily: typography.monoFamily,
    flexShrink: 0,
  },
  eventDescription: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  severityDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    flexShrink: 0,
  },
}

function severityBadgeStyle(severity: string): React.CSSProperties {
  const color = SEVERITY_COLORS[severity] ?? colors.textMuted
  return {
    ...styles.summaryBadge,
    background: `${color}20`,
    color,
  }
}

export default function LiveAlertsPanel() {
  const allItems = useDashboardStore((s) => s.items)
  const items = useMemo(() => allItems.filter((i) => i.type === 'alerts'), [allItems])
  const { events, counts } = useMemo(() => {
    const allEvents: TimelineEvent[] = []
    for (const item of items) {
      if (item.incidentTimeline) {
        allEvents.push(...item.incidentTimeline.events)
      }
    }

    // Sort by severity (critical first)
    allEvents.sort((a, b) =>
      (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
    )

    // Count by severity
    const c: Record<string, number> = {}
    for (const e of allEvents) {
      c[e.severity] = (c[e.severity] ?? 0) + 1
    }

    return { events: allEvents, counts: c }
  }, [items])

  return (
    <div>
      {/* Summary stats */}
      <div style={styles.summaryRow}>
        {Object.entries(counts).map(([severity, count]) => (
          <span key={severity} style={severityBadgeStyle(severity)}>
            {severity.charAt(0).toUpperCase() + severity.slice(1)}: {count}
          </span>
        ))}
      </div>

      {/* Event cards */}
      {events.map((event) => (
        <div key={event.id} style={styles.eventCard}>
          <div style={styles.eventHeader}>
            <span
              style={{
                ...styles.severityDot,
                background: SEVERITY_COLORS[event.severity] ?? colors.textMuted,
              }}
            />
            <span style={severityBadgeStyle(event.severity)}>
              {event.severity}
            </span>
            <span style={styles.eventTitle}>{event.title}</span>
            <span style={styles.eventTimestamp}>
              {new Date(event.timestamp).toLocaleTimeString()}
            </span>
          </div>
          {event.description && (
            <div style={styles.eventDescription}>{event.description}</div>
          )}
        </div>
      ))}
    </div>
  )
}
