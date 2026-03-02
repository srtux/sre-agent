/**
 * Reusable glass card wrapper for dashboard items.
 * Provides title, subtitle, timestamp, and remove button.
 */
import { useMemo } from 'react'
import { colors, typography, radii, spacing } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

interface DashboardCardWrapperProps {
  title: string
  subtitle?: string
  timestamp?: string
  onRemove?: () => void
  children: React.ReactNode
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    ...glassCard(),
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  titleGroup: {
    flex: 1,
    minWidth: 0,
  },
  title: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.textPrimary,
    margin: 0,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  subtitle: {
    fontSize: typography.sizes.sm,
    color: colors.textMuted,
    marginTop: 2,
  },
  timestamp: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    whiteSpace: 'nowrap' as const,
    flexShrink: 0,
  },
  removeBtn: {
    background: 'transparent',
    border: 'none',
    color: colors.textMuted,
    cursor: 'pointer',
    padding: 4,
    fontSize: '14px',
    lineHeight: 1,
    borderRadius: radii.sm,
    flexShrink: 0,
  },
}

export default function DashboardCardWrapper({
  title,
  subtitle,
  timestamp,
  onRemove,
  children,
}: DashboardCardWrapperProps) {
  const relativeTime = useMemo(
    () => (timestamp ? formatRelativeTime(timestamp) : undefined),
    [timestamp],
  )

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <div style={styles.titleGroup}>
          <div style={styles.title} title={title}>{title}</div>
          {subtitle && <div style={styles.subtitle}>{subtitle}</div>}
        </div>
        {relativeTime && <span style={styles.timestamp}>{relativeTime}</span>}
        {onRemove && (
          <button style={styles.removeBtn} onClick={onRemove} title="Remove">
            ✕
          </button>
        )}
      </div>
      {children}
    </div>
  )
}
