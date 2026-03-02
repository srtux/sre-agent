import type { MetricsDashboardData, DashboardMetric } from '../../types/sre'
import { colors, typography, spacing } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

const STATUS_DOT: Record<string, string> = {
  normal: colors.success,
  warning: colors.warning,
  critical: colors.error,
}

function trend(current: number, previous?: number): { symbol: string; color: string } | null {
  if (previous == null) return null
  if (current > previous) return { symbol: '\u2191', color: colors.error }
  if (current < previous) return { symbol: '\u2193', color: colors.success }
  return { symbol: '\u2192', color: colors.textMuted }
}

function MetricCard({ metric }: { metric: DashboardMetric }) {
  const t = trend(metric.currentValue, metric.previousValue)

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm }}>
        <span style={{ fontSize: typography.sizes.sm, color: colors.textSecondary, fontWeight: 500 }}>
          {metric.name}
        </span>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: STATUS_DOT[metric.status] ?? colors.textMuted,
            flexShrink: 0,
          }}
        />
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: spacing.sm }}>
        <span style={{ fontSize: typography.sizes.title, fontWeight: 700, color: colors.textPrimary }}>
          {metric.currentValue.toLocaleString()}
        </span>
        <span style={{ fontSize: typography.sizes.sm, color: colors.textMuted }}>
          {metric.unit}
        </span>
      </div>

      {t && metric.previousValue != null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: spacing.xs }}>
          <span style={{ color: t.color, fontWeight: 600 }}>{t.symbol}</span>
          <span style={{ fontSize: typography.sizes.xs, color: colors.textMuted }}>
            vs {metric.previousValue.toLocaleString()} {metric.unit}
          </span>
        </div>
      )}

      {metric.anomalyDescription && (
        <div style={{ marginTop: spacing.sm, fontSize: typography.sizes.xs, color: colors.warning, fontStyle: 'italic' }}>
          {metric.anomalyDescription}
        </div>
      )}
    </div>
  )
}

export default function MetricsDashboard({ data }: { data: MetricsDashboardData }) {
  if (!data.metrics.length) {
    return (
      <div style={{ ...glassCard(), padding: spacing.lg, color: colors.textMuted, textAlign: 'center' }}>
        No metrics data
      </div>
    )
  }

  return (
    <div style={gridStyle}>
      {data.metrics.map((m) => (
        <MetricCard key={m.id} metric={m} />
      ))}
    </div>
  )
}

const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap: spacing.md,
}

const cardStyle: React.CSSProperties = {
  ...glassCard(),
  padding: spacing.md,
  display: 'flex',
  flexDirection: 'column',
}
