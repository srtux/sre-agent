import { colors, spacing, radii, typography } from '../../theme/tokens'

interface SourceBadgeProps {
  source: 'agent' | 'manual'
}

export default function SourceBadge({ source }: SourceBadgeProps) {
  const isAgent = source === 'agent'
  return (
    <span
      style={{
        display: 'inline-block',
        padding: `1px ${spacing.sm}px`,
        borderRadius: radii.round,
        fontSize: typography.sizes.xs,
        fontWeight: typography.weights.medium,
        lineHeight: '16px',
        background: isAgent ? `${colors.cyan}22` : `${colors.purple}22`,
        color: isAgent ? colors.cyan : colors.purple,
      }}
    >
      {isAgent ? 'Agent' : 'Manual'}
    </span>
  )
}
