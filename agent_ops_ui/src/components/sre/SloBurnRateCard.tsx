import type { SloBurnRate } from '../../types/sre'
import { colors, spacing, radii, typography } from '../../theme/tokens'
import { glassCardElevated } from '../../theme/glassStyles'

interface SloBurnRateCardProps {
  data: SloBurnRate
}

function getBudgetColor(remaining: number): string {
  if (remaining > 50) return colors.success
  if (remaining > 20) return colors.warning
  return colors.error
}

function getBudgetBg(remaining: number): string {
  if (remaining > 50) return colors.successDim
  if (remaining > 20) return colors.warningDim
  return colors.errorDim
}

export default function SloBurnRateCard({ data }: SloBurnRateCardProps) {
  const budgetColor = getBudgetColor(data.budgetRemaining)
  const budgetBg = getBudgetBg(data.budgetRemaining)
  const objectiveDisplay = `${(data.objective * 100).toFixed(1)}%`

  return (
    <div style={{ ...glassCardElevated(), ...styles.card }}>
      <div style={styles.header}>
        <h3 style={styles.title}>{data.sloName}</h3>
        <span style={styles.objective}>{objectiveDisplay}</span>
      </div>

      {/* Progress bar */}
      <div style={styles.progressSection}>
        <div style={styles.progressLabel}>
          <span style={{ color: colors.textSecondary, fontSize: typography.sizes.sm }}>
            Budget Remaining
          </span>
          <span style={{ color: budgetColor, fontWeight: typography.weights.semibold, fontSize: typography.sizes.md }}>
            {data.budgetRemaining.toFixed(1)}%
          </span>
        </div>
        <div style={styles.progressTrack}>
          <div
            style={{
              ...styles.progressFill,
              width: `${Math.min(100, Math.max(0, data.budgetRemaining))}%`,
              background: budgetColor,
            }}
          />
        </div>
      </div>

      {/* Current burn rate */}
      <div style={{ ...styles.burnRate, background: budgetBg }}>
        <span style={{ color: colors.textSecondary, fontSize: typography.sizes.sm }}>
          Current Burn Rate
        </span>
        <span style={{ color: budgetColor, fontSize: typography.sizes.xxl, fontWeight: typography.weights.bold }}>
          {data.currentBurnRate.toFixed(2)}x
        </span>
      </div>

      {/* Multi-window breakdown */}
      {data.windows.length > 0 && (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Window</th>
              <th style={styles.th}>Burn Rate</th>
              <th style={styles.th}>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.windows.map((w, i) => (
              <tr key={i}>
                <td style={styles.td}>{w.duration}</td>
                <td style={styles.td}>{w.burnRate.toFixed(2)}x</td>
                <td style={styles.td}>
                  <span
                    style={{
                      color: w.isExhausted ? colors.error : colors.success,
                      fontSize: typography.sizes.sm,
                      fontWeight: typography.weights.medium,
                    }}
                  >
                    {w.isExhausted ? 'Exhausted' : 'OK'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
    justifyContent: 'space-between',
  },
  title: {
    margin: 0,
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
  },
  objective: {
    fontSize: typography.sizes.sm,
    color: colors.cyan,
    fontWeight: typography.weights.medium,
    padding: `2px ${spacing.sm}px`,
    borderRadius: radii.round,
    background: `${colors.cyan}18`,
  },
  progressSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.xs,
  },
  progressLabel: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  progressTrack: {
    height: 6,
    background: colors.surface,
    borderRadius: radii.round,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: radii.round,
    transition: 'width 0.3s ease',
  },
  burnRate: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: `${spacing.md}px ${spacing.lg}px`,
    borderRadius: radii.md,
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
}
