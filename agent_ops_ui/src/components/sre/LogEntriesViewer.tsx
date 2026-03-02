import { useState, useMemo } from 'react'
import type { LogEntriesData, SreLogEntry } from '../../types/sre'
import { colors, typography, spacing, radii } from '../../theme/tokens'
import { glassCard, glassInput } from '../../theme/glassStyles'

type SeverityFilter = 'ALL' | 'ERROR' | 'WARNING' | 'INFO' | 'DEBUG'

const SEVERITY_COLORS: Record<string, string> = {
  ERROR: colors.severityError,
  WARNING: colors.severityWarning,
  INFO: colors.severityInfo,
  DEBUG: colors.severityDebug,
  CRITICAL: colors.severityCritical,
  DEFAULT: colors.severityDefault,
}

function severityBadge(severity: string): React.CSSProperties {
  const color = SEVERITY_COLORS[severity.toUpperCase()] ?? SEVERITY_COLORS.DEFAULT
  return {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: radii.round,
    fontSize: '10px',
    fontWeight: 600,
    color,
    background: `${color}20`,
    minWidth: 50,
    textAlign: 'center',
  }
}

function payloadPreview(entry: SreLogEntry): string {
  if (entry.payloadPreview) return entry.payloadPreview
  if (typeof entry.payload === 'string') return entry.payload.slice(0, 200)
  return JSON.stringify(entry.payload).slice(0, 200)
}

export default function LogEntriesViewer({ data }: { data: LogEntriesData }) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<SeverityFilter>('ALL')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    let entries = data.entries
    if (filter !== 'ALL') {
      entries = entries.filter((e) => e.severity.toUpperCase() === filter)
    }
    if (search) {
      const q = search.toLowerCase()
      entries = entries.filter(
        (e) =>
          payloadPreview(e).toLowerCase().includes(q) ||
          e.severity.toLowerCase().includes(q),
      )
    }
    return entries
  }, [data.entries, filter, search])

  const chips: SeverityFilter[] = ['ALL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

  return (
    <div style={{ ...glassCard(), padding: spacing.md, minHeight: 200 }}>
      {/* Search + filters */}
      <div style={{ display: 'flex', gap: spacing.sm, marginBottom: spacing.md, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Search logs..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ ...glassInput(), padding: '6px 10px', fontSize: typography.sizes.sm, flex: 1, minWidth: 160 }}
        />
        <div style={{ display: 'flex', gap: 4 }}>
          {chips.map((c) => (
            <button
              key={c}
              onClick={() => setFilter(c)}
              style={{
                background: filter === c ? colors.primary : 'transparent',
                border: `1px solid ${filter === c ? colors.primary : colors.surfaceBorder}`,
                borderRadius: radii.round,
                color: filter === c ? '#fff' : colors.textSecondary,
                padding: '3px 10px',
                fontSize: typography.sizes.xs,
                cursor: 'pointer',
                fontWeight: filter === c ? 600 : 400,
                transition: 'all 0.15s ease',
              }}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Entries */}
      <div style={{ overflowY: 'auto', maxHeight: 420 }}>
        {filtered.length === 0 && (
          <div style={{ color: colors.textMuted, fontSize: typography.sizes.sm, textAlign: 'center', padding: spacing.xl }}>
            No log entries match filters
          </div>
        )}
        {filtered.map((entry) => {
          const isExpanded = expandedId === entry.insertId
          return (
            <div
              key={entry.insertId}
              onClick={() => setExpandedId(isExpanded ? null : entry.insertId)}
              style={{
                padding: `${spacing.sm}px ${spacing.md}px`,
                borderBottom: `1px solid ${colors.surfaceBorder}`,
                cursor: 'pointer',
                transition: 'background 0.15s ease',
                background: isExpanded ? colors.cardHover : 'transparent',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                <span style={{ fontSize: '10px', color: colors.textMuted, fontFamily: typography.monoFamily, minWidth: 150, flexShrink: 0 }}>
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
                <span style={severityBadge(entry.severity)}>
                  {entry.severity}
                </span>
                <span style={{ fontSize: typography.sizes.sm, color: colors.textSecondary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {payloadPreview(entry)}
                </span>
              </div>
              {isExpanded && (
                <pre style={expandedStyle}>
                  {typeof entry.payload === 'string'
                    ? entry.payload
                    : JSON.stringify(entry.payload, null, 2)}
                </pre>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const expandedStyle: React.CSSProperties = {
  marginTop: spacing.sm,
  padding: spacing.sm,
  background: colors.background,
  borderRadius: radii.md,
  fontSize: typography.sizes.xs,
  fontFamily: typography.monoFamily,
  color: colors.textPrimary,
  maxHeight: 300,
  overflow: 'auto',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-all',
}
