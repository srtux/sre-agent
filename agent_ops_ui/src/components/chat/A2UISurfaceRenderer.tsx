/**
 * Renders an A2UI surface by looking up the component in the registry.
 * Falls back to a JSON view for unknown component names.
 */
import { colors, spacing, typography } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'
import type { Surface } from '../../types/a2ui'
import { unwrapComponentData } from '../../types/a2ui'
import { getComponent } from './ComponentRegistry'

interface Props {
  surface: Surface
}

const styles: Record<string, React.CSSProperties> = {
  fallbackCard: {
    ...glassCard(),
    padding: `${spacing.sm}px ${spacing.md}px`,
    overflow: 'auto',
    maxHeight: 200,
  },
  fallbackHeader: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    marginBottom: spacing.xs,
    fontWeight: typography.weights.medium,
  },
  fallbackJson: {
    fontFamily: typography.monoFamily,
    fontSize: typography.sizes.xs,
    color: colors.textSecondary,
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-all' as const,
    lineHeight: 1.4,
  },
  renderingOverlay: {
    opacity: 0.7,
  },
}

export default function A2UISurfaceRenderer({ surface }: Props) {
  const Component = getComponent(surface.componentName)
  const data = unwrapComponentData(surface.data, surface.componentName)
  const isRendering = surface.status === 'rendering'

  const wrapperStyle: React.CSSProperties = isRendering
    ? styles.renderingOverlay
    : {}

  if (Component) {
    return (
      <div style={wrapperStyle}>
        <Component data={data} />
      </div>
    )
  }

  // Fallback: render raw JSON
  return (
    <div style={{ ...styles.fallbackCard, ...wrapperStyle }}>
      <div style={styles.fallbackHeader}>
        {surface.componentName}
        {isRendering && ' (loading...)'}
      </div>
      <pre style={styles.fallbackJson}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}
