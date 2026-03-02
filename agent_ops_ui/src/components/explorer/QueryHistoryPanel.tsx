/**
 * Recent query history panel.
 * Stored in localStorage. Max 20 entries.
 * Click to reload, delete individual entries.
 */
import { useState, useEffect, useCallback } from 'react'
import { History, X } from 'lucide-react'
import { colors, spacing, radii, typography, transitions } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

const HISTORY_KEY = 'sre_query_history'
const MAX_ENTRIES = 20

interface HistoryEntry {
  query: string
  language: string
  timestamp: string
}

interface QueryHistoryPanelProps {
  onSelect: (query: string, language: string) => void
}

const LANG_COLORS: Record<string, string> = {
  MQL: colors.primary,
  PromQL: colors.purple,
  SQL: colors.cyan,
  'Trace Filter': colors.warning,
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    ...glassCard(),
    padding: spacing.md,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.sm,
    maxHeight: 400,
    overflowY: 'auto',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.bold,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: `0 ${spacing.xs}px`,
  },
  entry: {
    ...glassCard({ padding: `${spacing.sm}px ${spacing.md}px` }),
    cursor: 'pointer',
    transition: transitions.fast,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    position: 'relative',
  },
  queryText: {
    fontFamily: typography.monoFamily,
    fontSize: typography.sizes.sm,
    color: colors.textPrimary,
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
    lineHeight: 1.4,
    wordBreak: 'break-all',
  },
  meta: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
  },
  badge: {
    padding: '1px 6px',
    borderRadius: radii.round,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.semibold,
  },
  deleteBtn: {
    position: 'absolute',
    top: spacing.sm,
    right: spacing.sm,
    background: 'transparent',
    border: 'none',
    color: colors.textDisabled,
    cursor: 'pointer',
    padding: 2,
    borderRadius: radii.sm,
    display: 'flex',
    transition: transitions.fast,
  },
  empty: {
    color: colors.textDisabled,
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    padding: spacing.lg,
  },
}

function loadHistory(): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch {
    return []
  }
}

function formatTime(ts: string): string {
  try {
    const d = new Date(ts)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffMin = Math.floor(diffMs / 60_000)
    if (diffMin < 1) return 'just now'
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHrs = Math.floor(diffMin / 60)
    if (diffHrs < 24) return `${diffHrs}h ago`
    return d.toLocaleDateString()
  } catch {
    return ts
  }
}

export default function QueryHistoryPanel({
  onSelect,
}: QueryHistoryPanelProps) {
  const [entries, setEntries] = useState<HistoryEntry[]>([])

  useEffect(() => {
    setEntries(loadHistory())
  }, [])

  const handleDelete = useCallback((index: number, e: React.MouseEvent) => {
    e.stopPropagation()
    setEntries((prev) => {
      const next = prev.filter((_, i) => i !== index).slice(0, MAX_ENTRIES)
      localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <History size={12} />
        Recent Queries
      </div>

      {entries.length === 0 ? (
        <div style={styles.empty}>No query history</div>
      ) : (
        entries.map((entry, i) => {
          const badgeColor = LANG_COLORS[entry.language] ?? colors.textMuted
          return (
            <div
              key={`${entry.timestamp}-${i}`}
              style={styles.entry}
              onClick={() => onSelect(entry.query, entry.language)}
              onMouseEnter={(e) => {
                ;(e.currentTarget as HTMLElement).style.background =
                  colors.cardHover
              }}
              onMouseLeave={(e) => {
                ;(e.currentTarget as HTMLElement).style.background =
                  colors.glassBg
              }}
            >
              <div style={styles.queryText}>{entry.query}</div>
              <div style={styles.meta}>
                <span
                  style={{
                    ...styles.badge,
                    background: `${badgeColor}22`,
                    color: badgeColor,
                  }}
                >
                  {entry.language}
                </span>
                <span>{formatTime(entry.timestamp)}</span>
              </div>
              <button
                type="button"
                style={styles.deleteBtn}
                onClick={(e) => handleDelete(i, e)}
                title="Remove from history"
                onMouseEnter={(e) => {
                  ;(e.currentTarget as HTMLElement).style.color = colors.error
                }}
                onMouseLeave={(e) => {
                  ;(e.currentTarget as HTMLElement).style.color =
                    colors.textDisabled
                }}
              >
                <X size={14} />
              </button>
            </div>
          )
        })
      )}
    </div>
  )
}
