import { useState } from 'react'
import type { ToolLog, ToolLogStatus } from '../../types/sre'
import { colors, typography, spacing, radii } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

const STATUS_ICON: Record<ToolLogStatus, string> = {
  running: '\u{1F504}',
  completed: '\u{2705}',
  error: '\u{274C}',
}

function formatDuration(ms?: number): string {
  if (ms == null) return ''
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function argsSummary(args?: Record<string, unknown>): string {
  if (!args) return ''
  const entries = Object.entries(args)
  if (entries.length === 0) return ''
  return entries
    .slice(0, 3)
    .map(([k, v]) => {
      const val = typeof v === 'string' ? v.slice(0, 30) : JSON.stringify(v).slice(0, 30)
      return `${k}=${val}`
    })
    .join(', ')
}

export default function ToolLogComponent({ data }: { data: ToolLog }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      style={{ ...glassCard(), padding: `${spacing.sm}px ${spacing.md}px`, cursor: 'pointer' }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Compact row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
        <span style={{ fontSize: '16px', flexShrink: 0 }}>
          {STATUS_ICON[data.status]}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <span style={{ fontWeight: 600, color: colors.textPrimary, fontSize: typography.sizes.md }}>
            {data.toolName}
          </span>
          {argsSummary(data.args) && (
            <span style={{ color: colors.textMuted, fontSize: typography.sizes.xs, marginLeft: spacing.sm, fontFamily: typography.monoFamily }}>
              {argsSummary(data.args)}
            </span>
          )}
        </div>
        {data.duration != null && (
          <span style={{ color: colors.textSecondary, fontSize: typography.sizes.sm, fontFamily: typography.monoFamily, flexShrink: 0 }}>
            {formatDuration(data.duration)}
          </span>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ marginTop: spacing.sm, borderTop: `1px solid ${colors.surfaceBorder}`, paddingTop: spacing.sm }}>
          {data.args && (
            <div style={{ marginBottom: spacing.sm }}>
              <div style={labelStyle}>Arguments</div>
              <pre style={jsonStyle}>{JSON.stringify(data.args, null, 2)}</pre>
            </div>
          )}
          {data.result !== undefined && (
            <div>
              <div style={labelStyle}>Result</div>
              <pre style={jsonStyle}>
                {typeof data.result === 'string' ? data.result : JSON.stringify(data.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  fontSize: typography.sizes.xs,
  color: colors.textMuted,
  fontWeight: 600,
  marginBottom: 2,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
}

const jsonStyle: React.CSSProperties = {
  fontFamily: typography.monoFamily,
  fontSize: typography.sizes.xs,
  color: colors.textPrimary,
  background: colors.background,
  padding: spacing.sm,
  borderRadius: radii.md,
  margin: 0,
  maxHeight: 200,
  overflow: 'auto',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-all',
}
