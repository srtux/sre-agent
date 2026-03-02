/**
 * Hero empty state shown when no messages exist.
 * Large SRE icon, title, subtitle, and suggestion chips.
 */
import { colors, spacing, typography } from '../../theme/tokens'
import SuggestionChips from './SuggestionChips'

interface Props {
  onSuggestionClick: (text: string) => void
}

const SUGGESTIONS = [
  'Investigate high latency in my service',
  'Show recent error logs',
  'Check SLO burn rates',
  'Analyze trace patterns',
]

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    textAlign: 'center',
    padding: spacing.xxxl,
    gap: spacing.lg,
  },
  icon: {
    fontSize: 64,
    lineHeight: 1,
    marginBottom: spacing.sm,
    filter: `drop-shadow(0 0 20px ${colors.cyan}40)`,
  },
  title: {
    fontSize: typography.sizes.hero,
    fontWeight: typography.weights.bold,
    fontFamily: typography.fontFamily,
    color: colors.textPrimary,
    margin: 0,
    background: `linear-gradient(135deg, ${colors.primary}, ${colors.cyan})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  subtitle: {
    fontSize: typography.sizes.lg,
    color: colors.textSecondary,
    fontFamily: typography.fontFamily,
    maxWidth: 480,
    lineHeight: 1.5,
    margin: 0,
  },
  chipsWrapper: {
    marginTop: spacing.xl,
    maxWidth: 600,
  },
}

export default function HeroEmptyState({ onSuggestionClick }: Props) {
  return (
    <div style={styles.container}>
      <div style={styles.icon}>🛡️</div>
      <h1 style={styles.title}>AutoSRE Investigation Assistant</h1>
      <p style={styles.subtitle}>
        AI-powered Site Reliability Engineering. Ask me to investigate
        incidents, analyze traces, check metrics, or diagnose issues.
      </p>
      <div style={styles.chipsWrapper}>
        <SuggestionChips
          suggestions={SUGGESTIONS}
          onSelect={onSuggestionClick}
        />
      </div>
    </div>
  )
}
