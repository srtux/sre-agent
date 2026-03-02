/**
 * Live council panel — displays Council of Experts synthesis results.
 * Mode badge, confidence bar, root cause, and expandable panel findings.
 */
import { useState, useMemo } from 'react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import DashboardCardWrapper from '../../common/DashboardCardWrapper'
import { colors, typography, radii, spacing } from '../../../theme/tokens'
import { glassCard } from '../../../theme/glassStyles'
import type { PanelFinding } from '../../../types/sre'

const MODE_COLORS: Record<string, string> = {
  fast: colors.info,
  standard: colors.primary,
  debate: colors.purple,
}

const styles: Record<string, React.CSSProperties> = {
  modeBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: `2px ${spacing.sm}px`,
    borderRadius: radii.round,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.semibold,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  headerRow: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.lg,
    flexWrap: 'wrap' as const,
  },
  confidenceContainer: {
    flex: 1,
    minWidth: 120,
  },
  confidenceLabel: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    marginBottom: 4,
  },
  confidenceBar: {
    height: 6,
    borderRadius: radii.round,
    background: colors.surfaceBorder,
    overflow: 'hidden',
  },
  confidenceFill: {
    height: '100%',
    borderRadius: radii.round,
    transition: 'width 0.3s ease',
  },
  confidenceValue: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
    marginLeft: spacing.sm,
  },
  section: {
    marginBottom: spacing.lg,
  },
  sectionTitle: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  sectionContent: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    lineHeight: 1.6,
  },
  findingCard: {
    ...glassCard({ padding: spacing.md }),
    marginBottom: spacing.sm,
    cursor: 'pointer',
  },
  findingHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
  },
  findingName: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.textPrimary,
    flex: 1,
  },
  findingConfidence: {
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.semibold,
    padding: `2px ${spacing.sm}px`,
    borderRadius: radii.round,
    flexShrink: 0,
  },
  findingDetails: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTop: `1px solid rgba(51, 65, 85, 0.3)`,
    lineHeight: 1.6,
  },
}

function confidenceColor(value: number): string {
  if (value >= 80) return colors.success
  if (value >= 50) return colors.warning
  return colors.error
}

function FindingCard({ finding }: { finding: PanelFinding }) {
  const [expanded, setExpanded] = useState(false)
  const cColor = confidenceColor(finding.confidence)

  return (
    <div style={styles.findingCard} onClick={() => setExpanded((p) => !p)}>
      <div style={styles.findingHeader}>
        <span style={{ fontSize: '12px' }}>{expanded ? '▼' : '▶'}</span>
        <span style={styles.findingName}>{finding.panelName}</span>
        <span style={{
          ...styles.findingConfidence,
          background: `${cColor}20`,
          color: cColor,
        }}>
          {finding.confidence}%
        </span>
      </div>
      <div style={{
        fontSize: typography.sizes.sm,
        color: colors.textSecondary,
        marginTop: 4,
      }}>
        {finding.summary}
      </div>
      {expanded && finding.details && (
        <div style={styles.findingDetails}>{finding.details}</div>
      )}
    </div>
  )
}

function CouncilCard({ item }: { item: ReturnType<ReturnType<typeof useDashboardStore.getState>['itemsOfType']>[number] }) {
  const removeItem = useDashboardStore((s) => s.removeItem)
  const data = item.councilSynthesis
  if (!data) return null

  const modeColor = MODE_COLORS[data.mode] ?? colors.textMuted
  const cColor = confidenceColor(data.overallConfidence)

  return (
    <DashboardCardWrapper
      title={data.title}
      subtitle={data.mode === 'debate' && data.debateRounds ? `${data.debateRounds} debate rounds` : undefined}
      timestamp={item.timestamp}
      onRemove={() => removeItem(item.id)}
    >
      {/* Mode + Confidence */}
      <div style={styles.headerRow}>
        <span style={{
          ...styles.modeBadge,
          background: `${modeColor}20`,
          color: modeColor,
        }}>
          {data.mode}
        </span>

        <div style={styles.confidenceContainer}>
          <div style={styles.confidenceLabel}>Overall Confidence</div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ ...styles.confidenceBar, flex: 1 }}>
              <div style={{
                ...styles.confidenceFill,
                width: `${data.overallConfidence}%`,
                background: cColor,
              }} />
            </div>
            <span style={{ ...styles.confidenceValue, color: cColor }}>
              {data.overallConfidence}%
            </span>
          </div>
        </div>
      </div>

      {/* Root cause */}
      {data.rootCause && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Root Cause</div>
          <div style={styles.sectionContent}>{data.rootCause}</div>
        </div>
      )}

      {/* Impact */}
      {data.impact && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Impact</div>
          <div style={styles.sectionContent}>{data.impact}</div>
        </div>
      )}

      {/* Recommendation */}
      {data.recommendation && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Recommendation</div>
          <div style={styles.sectionContent}>{data.recommendation}</div>
        </div>
      )}

      {/* Panel findings */}
      {data.findings.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Panel Findings ({data.findings.length})</div>
          {data.findings.map((f, i) => (
            <FindingCard key={`${f.panelName}-${i}`} finding={f} />
          ))}
        </div>
      )}
    </DashboardCardWrapper>
  )
}

export default function LiveCouncilPanel() {
  const allItems = useDashboardStore((s) => s.items)
  const items = useMemo(() => allItems.filter((i) => i.type === 'council'), [allItems])

  return (
    <div>
      {items.map((item) => (
        <CouncilCard key={item.id} item={item} />
      ))}
    </div>
  )
}
