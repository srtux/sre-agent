import { useState } from 'react'
import type { Postmortem } from '../../types/sre'
import { colors, spacing, typography, transitions } from '../../theme/tokens'
import { glassCardElevated, statusBadge } from '../../theme/glassStyles'

interface PostmortemCardProps {
  data: Postmortem
}

type Section = 'timeline' | 'rootCause' | 'impact' | 'actionItems'

const severityMap: Record<string, 'critical' | 'error' | 'warning' | 'info'> = {
  critical: 'critical',
  high: 'error',
  medium: 'warning',
  low: 'info',
}

export default function PostmortemCard({ data }: PostmortemCardProps) {
  const [expanded, setExpanded] = useState<Set<Section>>(new Set())

  const toggle = (section: Section) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(section)) next.delete(section)
      else next.add(section)
      return next
    })
  }

  const sev = severityMap[data.severity.toLowerCase()] ?? 'info'

  return (
    <div style={{ ...glassCardElevated(), ...styles.card }}>
      <div style={styles.header}>
        <h3 style={styles.title}>{data.title}</h3>
        <span style={statusBadge(sev)}>{data.severity}</span>
      </div>

      <p style={styles.summary}>{data.summary}</p>

      {/* Timeline */}
      <button style={styles.sectionToggle} onClick={() => toggle('timeline')}>
        <span>{expanded.has('timeline') ? '\u25BC' : '\u25B6'}</span>
        <span>Timeline ({data.timeline.length} events)</span>
      </button>
      {expanded.has('timeline') && (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Time</th>
              <th style={styles.th}>Event</th>
            </tr>
          </thead>
          <tbody>
            {data.timeline.map((entry, i) => (
              <tr key={i}>
                <td style={styles.td}>{entry.time}</td>
                <td style={styles.td}>{entry.event}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Root Cause */}
      <button style={styles.sectionToggle} onClick={() => toggle('rootCause')}>
        <span>{expanded.has('rootCause') ? '\u25BC' : '\u25B6'}</span>
        <span>Root Cause</span>
      </button>
      {expanded.has('rootCause') && (
        <p style={styles.sectionContent}>{data.rootCause}</p>
      )}

      {/* Impact */}
      <button style={styles.sectionToggle} onClick={() => toggle('impact')}>
        <span>{expanded.has('impact') ? '\u25BC' : '\u25B6'}</span>
        <span>Impact</span>
      </button>
      {expanded.has('impact') && (
        <p style={styles.sectionContent}>{data.impact}</p>
      )}

      {/* Action Items */}
      <button style={styles.sectionToggle} onClick={() => toggle('actionItems')}>
        <span>{expanded.has('actionItems') ? '\u25BC' : '\u25B6'}</span>
        <span>Action Items ({data.actionItems.length})</span>
      </button>
      {expanded.has('actionItems') && (
        <ul style={styles.checklist}>
          {data.actionItems.map((item, i) => (
            <li key={i} style={styles.checkItem}>
              <input type="checkbox" style={styles.checkbox} />
              <span style={styles.checkText}>
                {item.description}
                {item.owner && (
                  <span style={styles.owner}> — {item.owner}</span>
                )}
                {item.priority && (
                  <span style={styles.priority}> [{item.priority}]</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    padding: spacing.xl,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.md,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.md,
  },
  title: {
    margin: 0,
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
    flex: 1,
  },
  summary: {
    margin: 0,
    fontSize: typography.sizes.md,
    color: colors.textSecondary,
    lineHeight: 1.5,
  },
  sectionToggle: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    background: 'none',
    border: 'none',
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    padding: `${spacing.xs}px 0`,
    transition: transitions.fast,
  },
  sectionContent: {
    margin: 0,
    fontSize: typography.sizes.md,
    color: colors.textSecondary,
    lineHeight: 1.5,
    paddingLeft: spacing.xl,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: typography.sizes.sm,
  },
  th: {
    textAlign: 'left',
    padding: `${spacing.xs}px ${spacing.sm}px`,
    color: colors.textMuted,
    borderBottom: `1px solid ${colors.surfaceBorder}`,
    fontWeight: typography.weights.medium,
  },
  td: {
    padding: `${spacing.xs}px ${spacing.sm}px`,
    color: colors.textSecondary,
    borderBottom: `1px solid ${colors.surfaceBorder}`,
  },
  checklist: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
    paddingLeft: spacing.xl,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.xs,
  },
  checkItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  checkbox: {
    marginTop: 3,
    accentColor: colors.cyan,
  },
  checkText: {
    fontSize: typography.sizes.md,
    color: colors.textSecondary,
    lineHeight: 1.4,
  },
  owner: {
    color: colors.textMuted,
    fontSize: typography.sizes.sm,
  },
  priority: {
    color: colors.warning,
    fontSize: typography.sizes.sm,
  },
}
