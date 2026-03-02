import { colors, spacing, radii, typography, transitions } from '../../theme/tokens'

interface ErrorBannerProps {
  message: string
  onDismiss?: () => void
}

export default function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div style={styles.banner}>
      <span style={styles.icon}>{'\u26A0'}</span>
      <span style={styles.message}>{message}</span>
      {onDismiss && (
        <button
          style={styles.dismiss}
          onClick={onDismiss}
          aria-label="Dismiss error"
        >
          {'\u00D7'}
        </button>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  banner: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    padding: `${spacing.md}px ${spacing.lg}px`,
    background: colors.errorDim,
    border: `1px solid rgba(255, 82, 82, 0.3)`,
    borderRadius: radii.md,
    width: '100%',
    boxSizing: 'border-box',
  },
  icon: {
    color: colors.error,
    fontSize: typography.sizes.lg,
    flexShrink: 0,
  },
  message: {
    flex: 1,
    color: colors.error,
    fontSize: typography.sizes.md,
  },
  dismiss: {
    background: 'none',
    border: 'none',
    color: colors.error,
    cursor: 'pointer',
    fontSize: typography.sizes.xl,
    padding: spacing.xs,
    lineHeight: 1,
    opacity: 0.7,
    transition: transitions.fast,
    flexShrink: 0,
  },
}
