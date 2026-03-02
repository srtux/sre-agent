import type { CouncilSynthesisData } from '../../types/sre'
import { colors, spacing, radii, typography } from '../../theme/tokens'
import { glassCard, statusBadge } from '../../theme/glassStyles'

interface CouncilActivityGraphProps {
  data: CouncilSynthesisData
}

const modeColors: Record<string, string> = {
  fast: colors.success,
  standard: colors.cyan,
  debate: colors.warning,
}

export default function CouncilActivityGraph({ data }: CouncilActivityGraphProps) {
  const modeColor = modeColors[data.mode] ?? colors.cyan

  return (
    <div style={{ ...glassCard(), ...styles.container }}>
      <h3 style={styles.title}>{data.title}</h3>

      <div style={styles.flow}>
        {/* Mode badge */}
        <div style={{ ...styles.modeNode, borderColor: modeColor }}>
          <span style={{ color: modeColor, fontWeight: typography.weights.semibold }}>
            {data.mode.toUpperCase()}
          </span>
          {data.debateRounds != null && (
            <span style={styles.debateLabel}>{data.debateRounds} rounds</span>
          )}
        </div>

        {/* Connector line */}
        <div style={styles.connector} />

        {/* Panel cards */}
        <div style={styles.panels}>
          {data.findings.map((finding, i) => (
            <div key={i} style={styles.panelCard}>
              <div style={styles.panelHeader}>
                <span style={styles.panelName}>{finding.panelName}</span>
                {finding.severity && (
                  <span
                    style={statusBadge(
                      (finding.severity.toLowerCase() as 'error' | 'warning' | 'info') || 'info',
                    )}
                  >
                    {finding.severity}
                  </span>
                )}
              </div>
              <p style={styles.panelSummary}>{finding.summary}</p>
              {/* Confidence bar */}
              <div style={styles.confidenceRow}>
                <div style={styles.confidenceTrack}>
                  <div
                    style={{
                      ...styles.confidenceFill,
                      width: `${Math.round(finding.confidence * 100)}%`,
                      background:
                        finding.confidence > 0.7
                          ? colors.success
                          : finding.confidence > 0.4
                            ? colors.warning
                            : colors.error,
                    }}
                  />
                </div>
                <span style={styles.confidenceLabel}>
                  {Math.round(finding.confidence * 100)}%
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Connector line */}
        <div style={styles.connector} />

        {/* Synthesis node */}
        <div style={styles.synthesisNode}>
          <span style={styles.synthesisTitle}>Synthesis</span>
          <div style={styles.synthesisConfidence}>
            <span style={styles.confidenceLabel}>
              Overall: {Math.round(data.overallConfidence * 100)}%
            </span>
          </div>
          {data.rootCause && (
            <p style={styles.synthesisText}>
              <strong>Root Cause:</strong> {data.rootCause}
            </p>
          )}
          {data.recommendation && (
            <p style={styles.synthesisText}>
              <strong>Recommendation:</strong> {data.recommendation}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: spacing.xl,
  },
  title: {
    margin: 0,
    marginBottom: spacing.lg,
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
  },
  flow: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 0,
  },
  modeNode: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: spacing.xs,
    padding: `${spacing.sm}px ${spacing.xl}px`,
    borderRadius: radii.round,
    border: '2px solid',
    background: colors.surface,
  },
  debateLabel: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
  },
  connector: {
    width: 2,
    height: 24,
    background: colors.surfaceBorder,
  },
  panels: {
    display: 'flex',
    gap: spacing.md,
    flexWrap: 'wrap',
    justifyContent: 'center',
    width: '100%',
  },
  panelCard: {
    flex: '1 1 200px',
    maxWidth: 280,
    background: colors.surface,
    border: `1px solid ${colors.surfaceBorder}`,
    borderRadius: radii.md,
    padding: spacing.md,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.xs,
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  panelName: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    color: colors.cyan,
  },
  panelSummary: {
    margin: 0,
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    lineHeight: 1.4,
  },
  confidenceRow: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
  },
  confidenceTrack: {
    flex: 1,
    height: 4,
    background: colors.background,
    borderRadius: radii.round,
    overflow: 'hidden',
  },
  confidenceFill: {
    height: '100%',
    borderRadius: radii.round,
    transition: 'width 0.3s ease',
  },
  confidenceLabel: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    whiteSpace: 'nowrap',
  },
  synthesisNode: {
    width: '100%',
    maxWidth: 500,
    background: `linear-gradient(135deg, ${colors.primary}18, ${colors.cyan}18)`,
    border: `1px solid ${colors.primary}44`,
    borderRadius: radii.lg,
    padding: spacing.lg,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.sm,
  },
  synthesisTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.primaryLight,
  },
  synthesisConfidence: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
  },
  synthesisText: {
    margin: 0,
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    lineHeight: 1.4,
  },
}
