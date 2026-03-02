import type { LogPattern } from '../../types/sre'
import { colors, typography, spacing, radii } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

const SEV_COLORS: Record<string, string> = {
  ERROR: colors.severityError,
  WARNING: colors.severityWarning,
  INFO: colors.severityInfo,
  DEBUG: colors.severityDebug,
  CRITICAL: colors.severityCritical,
}

function SeverityBar({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  if (total === 0) return null

  return (
    <div style={{ display: 'flex', height: 6, borderRadius: radii.round, overflow: 'hidden', width: '100%', marginTop: spacing.xs }}>
      {Object.entries(counts).map(([sev, count]) => {
        const pct = (count / total) * 100
        if (pct === 0) return null
        return (
          <div
            key={sev}
            title={`${sev}: ${count}`}
            style={{
              width: `${pct}%`,
              background: SEV_COLORS[sev.toUpperCase()] ?? colors.severityDefault,
              minWidth: pct > 0 ? 2 : 0,
            }}
          />
        )
      })}
    </div>
  )
}

export default function LogPatternViewer({ patterns }: { patterns: LogPattern[] }) {
  if (!patterns.length) {
    return (
      <div style={{ ...glassCard(), padding: spacing.lg, color: colors.textMuted, textAlign: 'center' }}>
        No log patterns
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
      {patterns.map((p, i) => (
        <div key={i} style={{ ...glassCard(), padding: spacing.md }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: spacing.sm }}>
            <pre style={templateStyle}>{p.template}</pre>
            <span style={countBadgeStyle}>{p.count}</span>
          </div>
          {p.severityCounts && <SeverityBar counts={p.severityCounts} />}
        </div>
      ))}
    </div>
  )
}

const templateStyle: React.CSSProperties = {
  fontFamily: typography.monoFamily,
  fontSize: typography.sizes.xs,
  color: colors.textPrimary,
  margin: 0,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-all',
  flex: 1,
}

const countBadgeStyle: React.CSSProperties = {
  background: colors.primary,
  color: '#fff',
  fontSize: typography.sizes.xs,
  fontWeight: 600,
  padding: '2px 8px',
  borderRadius: radii.round,
  flexShrink: 0,
}
