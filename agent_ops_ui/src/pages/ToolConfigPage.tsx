import { useState, useMemo } from 'react'
import { useToolConfigs, useUpdateToolConfig } from '../hooks/useToolConfig'
import type { ToolConfig } from '../hooks/useToolConfig'
import { colors, spacing, radii, typography, transitions } from '../theme/tokens'
import { glassCard, glassButton } from '../theme/glassStyles'
import ShimmerLoading from '../components/common/ShimmerLoading'
import ErrorBanner from '../components/common/ErrorBanner'

const categoryTabs = ['All', 'Investigation', 'Analysis', 'Discovery', 'Remediation'] as const
type Category = (typeof categoryTabs)[number]

export default function ToolConfigPage() {
  const [activeCategory, setActiveCategory] = useState<Category>('All')
  const [expandedTool, setExpandedTool] = useState<string | null>(null)

  const { data: tools, isLoading, error } = useToolConfigs()
  const updateMutation = useUpdateToolConfig()

  const filtered = useMemo(() => {
    if (!tools) return []
    if (activeCategory === 'All') return tools
    return tools.filter(
      (t) => t.category.toLowerCase() === activeCategory.toLowerCase(),
    )
  }, [tools, activeCategory])

  return (
    <div style={styles.container}>
      {/* Category tabs */}
      <div style={styles.tabs}>
        {categoryTabs.map((cat) => (
          <button
            key={cat}
            style={activeCategory === cat ? styles.tabActive : styles.tab}
            onClick={() => setActiveCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {error && (
        <ErrorBanner
          message={error instanceof Error ? error.message : 'Failed to load tool configs'}
        />
      )}

      {isLoading && (
        <div style={styles.grid}>
          {Array.from({ length: 8 }).map((_, i) => (
            <ShimmerLoading key={i} height={140} borderRadius={radii.lg} />
          ))}
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <p style={styles.empty}>No tools in this category.</p>
      )}

      {!isLoading && filtered.length > 0 && (
        <div style={styles.grid}>
          {filtered.map((tool) => (
            <ToolCard
              key={tool.name}
              tool={tool}
              expanded={expandedTool === tool.name}
              onToggle={() =>
                setExpandedTool(expandedTool === tool.name ? null : tool.name)
              }
              onToggleEnabled={(enabled) =>
                updateMutation.mutate({ name: tool.name, enabled })
              }
              isUpdating={
                updateMutation.isPending &&
                updateMutation.variables?.name === tool.name
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ToolCard({
  tool,
  expanded,
  onToggle,
  onToggleEnabled,
  isUpdating,
}: {
  tool: ToolConfig
  expanded: boolean
  onToggle: () => void
  onToggleEnabled: (enabled: boolean) => void
  isUpdating: boolean
}) {
  return (
    <div
      style={{
        ...glassCard(),
        ...styles.card,
        ...(expanded ? styles.cardExpanded : {}),
      }}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onToggle()
      }}
    >
      <div style={styles.cardHeader}>
        <h4 style={styles.cardTitle}>{tool.name}</h4>
        {/* Toggle switch */}
        <label
          style={styles.toggleLabel}
          onClick={(e) => e.stopPropagation()}
        >
          <input
            type="checkbox"
            checked={tool.enabled}
            disabled={isUpdating}
            onChange={(e) => onToggleEnabled(e.target.checked)}
            style={styles.toggleInput}
          />
          <span
            style={{
              ...styles.toggleTrack,
              background: tool.enabled ? colors.cyan : colors.surfaceLight,
            }}
          >
            <span
              style={{
                ...styles.toggleThumb,
                transform: tool.enabled ? 'translateX(16px)' : 'translateX(0)',
              }}
            />
          </span>
        </label>
      </div>

      <p style={styles.cardDesc}>{tool.description}</p>

      <div style={styles.cardFooter}>
        <span style={styles.categoryBadge}>{tool.category}</span>
        <button
          style={{ ...glassButton(), ...styles.testBtn }}
          onClick={(e) => {
            e.stopPropagation()
            // placeholder for test functionality
          }}
        >
          Test
        </button>
      </div>

      {expanded && (
        <div style={styles.expandedContent}>
          <p style={styles.expandedText}>
            <strong>Full Description:</strong> {tool.description}
          </p>
          <p style={styles.expandedText}>
            <strong>Category:</strong> {tool.category}
          </p>
          <p style={styles.expandedText}>
            <strong>Status:</strong>{' '}
            <span style={{ color: tool.enabled ? colors.success : colors.textMuted }}>
              {tool.enabled ? 'Enabled' : 'Disabled'}
            </span>
          </p>
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.lg,
    flex: 1,
    overflow: 'auto',
  },
  tabs: {
    display: 'flex',
    gap: spacing.xs,
    flexWrap: 'wrap',
  },
  tab: {
    padding: `${spacing.sm}px ${spacing.lg}px`,
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    cursor: 'pointer',
    border: `1px solid ${colors.surfaceBorder}`,
    borderRadius: radii.round,
    background: 'transparent',
    color: colors.textSecondary,
    transition: transitions.fast,
  },
  tabActive: {
    padding: `${spacing.sm}px ${spacing.lg}px`,
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    cursor: 'pointer',
    border: `1px solid ${colors.cyan}`,
    borderRadius: radii.round,
    background: `${colors.cyan}18`,
    color: colors.cyan,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: spacing.lg,
  },
  empty: {
    color: colors.textMuted,
    fontSize: typography.sizes.md,
    textAlign: 'center',
    padding: spacing.xxxl,
  },
  card: {
    padding: spacing.lg,
    cursor: 'pointer',
    transition: transitions.normal,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.sm,
  },
  cardExpanded: {
    background: colors.glassHover,
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitle: {
    margin: 0,
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
  },
  cardDesc: {
    margin: 0,
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    lineHeight: 1.4,
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  cardFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.xs,
  },
  categoryBadge: {
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.medium,
    color: colors.primaryLight,
    background: `${colors.primary}18`,
    padding: `2px ${spacing.sm}px`,
    borderRadius: radii.round,
  },
  testBtn: {
    padding: `${spacing.xs}px ${spacing.md}px`,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.medium,
  },
  expandedContent: {
    borderTop: `1px solid ${colors.surfaceBorder}`,
    paddingTop: spacing.md,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.xs,
  },
  expandedText: {
    margin: 0,
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    lineHeight: 1.4,
  },
  // Toggle switch styles
  toggleLabel: {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    cursor: 'pointer',
  },
  toggleInput: {
    position: 'absolute',
    opacity: 0,
    width: 0,
    height: 0,
  },
  toggleTrack: {
    display: 'inline-block',
    width: 36,
    height: 20,
    borderRadius: radii.round,
    position: 'relative',
    transition: transitions.fast,
  },
  toggleThumb: {
    position: 'absolute',
    top: 2,
    left: 2,
    width: 16,
    height: 16,
    borderRadius: '50%',
    background: '#fff',
    transition: transitions.fast,
  },
}
