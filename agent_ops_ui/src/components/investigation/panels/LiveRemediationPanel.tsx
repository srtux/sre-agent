/**
 * Live remediation panel — shows remediation plans with risk badges
 * and expandable step lists with commands.
 */
import { useState, useMemo } from 'react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import DashboardCardWrapper from '../../common/DashboardCardWrapper'
import { colors, typography, radii, spacing } from '../../../theme/tokens'
import { glassCard } from '../../../theme/glassStyles'

const RISK_COLORS: Record<string, string> = {
  high: colors.severityError,
  medium: colors.severityWarning,
  low: colors.success,
}

const styles: Record<string, React.CSSProperties> = {
  riskBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: `2px ${spacing.sm}px`,
    borderRadius: radii.round,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.semibold,
    textTransform: 'uppercase' as const,
  },
  stepsToggle: {
    background: 'transparent',
    border: 'none',
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    padding: `${spacing.xs}px 0`,
    marginTop: spacing.sm,
  },
  stepList: {
    listStyle: 'none',
    padding: 0,
    margin: `${spacing.sm}px 0 0`,
  },
  stepItem: {
    ...glassCard(),
    padding: spacing.md,
    marginBottom: spacing.sm,
    display: 'flex',
    gap: spacing.md,
  },
  stepNumber: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    background: `${colors.primary}20`,
    color: colors.primary,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.semibold,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  stepContent: {
    flex: 1,
    minWidth: 0,
  },
  stepDescription: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    lineHeight: 1.5,
  },
  stepCommand: {
    fontFamily: typography.monoFamily,
    fontSize: typography.sizes.xs,
    color: colors.cyan,
    background: 'rgba(6, 182, 212, 0.08)',
    padding: `${spacing.xs}px ${spacing.sm}px`,
    borderRadius: radii.sm,
    marginTop: spacing.xs,
    overflow: 'auto',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-all' as const,
  },
}

function RemediationCard({ item }: { item: ReturnType<ReturnType<typeof useDashboardStore.getState>['itemsOfType']>[number] }) {
  const [expanded, setExpanded] = useState(false)
  const removeItem = useDashboardStore((s) => s.removeItem)
  const plan = item.remediationPlan
  if (!plan) return null

  const riskColor = RISK_COLORS[plan.risk] ?? colors.textMuted

  return (
    <DashboardCardWrapper
      title={plan.issue}
      timestamp={item.timestamp}
      onRemove={() => removeItem(item.id)}
    >
      <span style={{
        ...styles.riskBadge,
        background: `${riskColor}20`,
        color: riskColor,
      }}>
        {plan.risk} risk
      </span>

      <button
        style={styles.stepsToggle}
        onClick={() => setExpanded((p) => !p)}
      >
        {expanded ? '▲ Hide steps' : `▼ Show ${plan.steps.length} steps`}
      </button>

      {expanded && (
        <ol style={styles.stepList}>
          {plan.steps.map((step, i) => (
            <li key={i} style={styles.stepItem}>
              <span style={styles.stepNumber}>{i + 1}</span>
              <div style={styles.stepContent}>
                <div style={styles.stepDescription}>{step.description}</div>
                {step.command && (
                  <div style={styles.stepCommand}>{step.command}</div>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </DashboardCardWrapper>
  )
}

export default function LiveRemediationPanel() {
  const allItems = useDashboardStore((s) => s.items)
  const items = useMemo(() => allItems.filter((i) => i.type === 'remediation'), [allItems])

  return (
    <div>
      {items.map((item) => (
        <RemediationCard key={item.id} item={item} />
      ))}
    </div>
  )
}
