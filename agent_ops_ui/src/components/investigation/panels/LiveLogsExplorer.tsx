/**
 * Live logs explorer — aggregates log entries with search, severity filter,
 * pattern summary, and expandable JSON payload.
 */
import { useState, useMemo } from 'react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import JsonPayloadViewer from '../../common/JsonPayloadViewer'
import { colors, typography, radii, spacing } from '../../../theme/tokens'
import { glassCard, glassInput } from '../../../theme/glassStyles'
import type { SreLogEntry, LogPattern } from '../../../types/sre'

type SeverityFilter = 'ALL' | 'ERROR' | 'WARNING' | 'INFO' | 'DEBUG' | 'CRITICAL'

const SEVERITY_FILTERS: Array<{ key: SeverityFilter; color: string }> = [
  { key: 'ALL', color: colors.textSecondary },
  { key: 'CRITICAL', color: colors.severityCritical },
  { key: 'ERROR', color: colors.severityError },
  { key: 'WARNING', color: colors.severityWarning },
  { key: 'INFO', color: colors.severityInfo },
  { key: 'DEBUG', color: colors.severityDebug },
]

const styles: Record<string, React.CSSProperties> = {
  searchRow: {
    display: 'flex',
    gap: spacing.sm,
    marginBottom: spacing.md,
    flexWrap: 'wrap' as const,
  },
  searchInput: {
    ...glassInput(),
    flex: 1,
    minWidth: 200,
    padding: `${spacing.sm}px ${spacing.md}px`,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
  },
  chips: {
    display: 'flex',
    gap: 4,
    flexWrap: 'wrap' as const,
  },
  chip: {
    padding: `${spacing.xs}px ${spacing.sm}px`,
    borderRadius: radii.round,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.medium,
    cursor: 'pointer',
    border: '1px solid transparent',
    transition: 'all 0.15s ease',
  },
  patternSection: {
    ...glassCard(),
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  patternTitle: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  patternRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: `${spacing.xs}px 0`,
    borderBottom: `1px solid rgba(51, 65, 85, 0.3)`,
  },
  patternTemplate: {
    fontFamily: typography.monoFamily,
    fontSize: typography.sizes.xs,
    color: colors.textSecondary,
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
    marginRight: spacing.sm,
  },
  patternCount: {
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.semibold,
    color: colors.cyan,
    flexShrink: 0,
  },
  logEntry: {
    ...glassCard(),
    padding: spacing.md,
    marginBottom: spacing.sm,
    cursor: 'pointer',
  },
  logHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
  },
  severityBadge: {
    padding: `2px ${spacing.sm}px`,
    borderRadius: radii.round,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.semibold,
  },
  logTimestamp: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    fontFamily: typography.monoFamily,
  },
  logPayload: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  resultCount: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
}

function severityBadgeStyle(severity: string): React.CSSProperties {
  const colorMap: Record<string, { bg: string; text: string }> = {
    CRITICAL: { bg: 'rgba(255, 23, 68, 0.15)', text: colors.severityCritical },
    ERROR: { bg: 'rgba(255, 82, 82, 0.15)', text: colors.severityError },
    WARNING: { bg: 'rgba(255, 171, 0, 0.15)', text: colors.severityWarning },
    INFO: { bg: 'rgba(41, 182, 246, 0.15)', text: colors.severityInfo },
    DEBUG: { bg: 'rgba(120, 144, 156, 0.15)', text: colors.severityDebug },
  }
  const c = colorMap[severity.toUpperCase()] ?? colorMap.DEBUG
  return {
    ...styles.severityBadge,
    background: c.bg,
    color: c.text,
  }
}

function LogEntryRow({ entry }: { entry: SreLogEntry }) {
  const [expanded, setExpanded] = useState(false)

  const preview = entry.payloadPreview
    ?? (typeof entry.payload === 'string' ? entry.payload : JSON.stringify(entry.payload))

  return (
    <div style={styles.logEntry} onClick={() => setExpanded((p) => !p)}>
      <div style={styles.logHeader}>
        <span style={severityBadgeStyle(entry.severity)}>{entry.severity}</span>
        <span style={styles.logTimestamp}>
          {new Date(entry.timestamp).toLocaleTimeString()}
        </span>
      </div>
      {!expanded && (
        <div style={styles.logPayload}>{preview}</div>
      )}
      {expanded && (
        <div style={{ marginTop: spacing.sm }}>
          <JsonPayloadViewer data={entry.payload} maxHeight={300} />
        </div>
      )}
    </div>
  )
}

export default function LiveLogsExplorer() {
  const allItems = useDashboardStore((s) => s.items)
  const items = useMemo(() => allItems.filter((i) => i.type === 'logs'), [allItems])
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('ALL')

  // Aggregate all entries and patterns
  const { allEntries, topPatterns } = useMemo(() => {
    const entries: SreLogEntry[] = []
    const patterns: LogPattern[] = []

    for (const item of items) {
      if (item.logEntries) entries.push(...item.logEntries.entries)
      if (item.logPatterns) patterns.push(...item.logPatterns)
    }

    // Sort entries newest first
    entries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

    // Top 3 patterns by count
    const sorted = [...patterns].sort((a, b) => b.count - a.count).slice(0, 3)

    return { allEntries: entries, topPatterns: sorted }
  }, [items])

  // Filter entries
  const filtered = useMemo(() => {
    let result = allEntries

    if (severityFilter !== 'ALL') {
      result = result.filter((e) => e.severity.toUpperCase() === severityFilter)
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter((e) => {
        const text = typeof e.payload === 'string' ? e.payload : JSON.stringify(e.payload)
        return text.toLowerCase().includes(q)
      })
    }

    return result
  }, [allEntries, severityFilter, search])

  return (
    <div>
      {/* Search + severity filter */}
      <div style={styles.searchRow}>
        <input
          style={styles.searchInput}
          placeholder="Search logs..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div style={{ ...styles.chips, marginBottom: spacing.md }}>
        {SEVERITY_FILTERS.map(({ key, color }) => (
          <button
            key={key}
            style={{
              ...styles.chip,
              background: severityFilter === key ? `${color}20` : 'transparent',
              color: severityFilter === key ? color : colors.textMuted,
              borderColor: severityFilter === key ? `${color}40` : 'transparent',
            }}
            onClick={() => setSeverityFilter(key)}
          >
            {key}
          </button>
        ))}
      </div>

      {/* Pattern summary */}
      {topPatterns.length > 0 && (
        <div style={styles.patternSection}>
          <div style={styles.patternTitle}>Top Patterns</div>
          {topPatterns.map((p, i) => (
            <div key={i} style={styles.patternRow}>
              <span style={styles.patternTemplate}>{p.template}</span>
              <span style={styles.patternCount}>{p.count}x</span>
            </div>
          ))}
        </div>
      )}

      {/* Log entries */}
      <div style={styles.resultCount}>{filtered.length} entries</div>
      <div style={{ maxHeight: 600, overflow: 'auto' }}>
        {filtered.map((entry) => (
          <LogEntryRow key={entry.insertId} entry={entry} />
        ))}
      </div>
    </div>
  )
}
