import { useState } from 'react'
import { useHelp } from '../hooks/useHelp'
import type { HelpItem } from '../hooks/useHelp'
import { colors, spacing, radii, typography, transitions } from '../theme/tokens'
import { glassCard, glassInput } from '../theme/glassStyles'
import ShimmerLoading from '../components/common/ShimmerLoading'
import ErrorBanner from '../components/common/ErrorBanner'

export default function HelpPage() {
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined)
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: items, isLoading, error } = useHelp(selectedCategory)

  const filtered = (items ?? []).filter((item) => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      item.title.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q)
    )
  })

  const categories = Array.from(new Set((items ?? []).map((i) => i.category))).sort()

  return (
    <div style={styles.layout}>
      {/* Sidebar */}
      <div style={styles.sidebar}>
        <h3 style={styles.sidebarTitle}>Categories</h3>
        <button
          style={selectedCategory === undefined ? styles.catActive : styles.catBtn}
          onClick={() => setSelectedCategory(undefined)}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            style={selectedCategory === cat ? styles.catActive : styles.catBtn}
            onClick={() => setSelectedCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Main */}
      <div style={styles.main}>
        {/* Search */}
        <input
          type="text"
          placeholder="Search help articles..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ ...glassInput(), ...styles.searchInput }}
        />

        {error && (
          <ErrorBanner message={error instanceof Error ? error.message : 'Failed to load help'} />
        )}

        {isLoading && (
          <div style={styles.grid}>
            {Array.from({ length: 6 }).map((_, i) => (
              <ShimmerLoading key={i} height={120} borderRadius={radii.lg} />
            ))}
          </div>
        )}

        {!isLoading && filtered.length === 0 && (
          <p style={styles.empty}>No help articles found.</p>
        )}

        {!isLoading && filtered.length > 0 && (
          <div style={styles.grid}>
            {filtered.map((item) => (
              <HelpCard
                key={item.id}
                item={item}
                expanded={expandedId === item.id}
                onToggle={() =>
                  setExpandedId(expandedId === item.id ? null : item.id)
                }
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function HelpCard({
  item,
  expanded,
  onToggle,
}: {
  item: HelpItem
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <div
      style={{ ...glassCard(), ...styles.card, ...(expanded ? styles.cardExpanded : {}) }}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onToggle()
      }}
    >
      <div style={styles.cardHeader}>
        <h4 style={styles.cardTitle}>{item.title}</h4>
        <span style={styles.badge}>{item.category}</span>
      </div>
      <p style={styles.cardDesc}>{item.description}</p>
      {expanded && <p style={styles.cardContent}>{item.content}</p>}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  layout: {
    display: 'flex',
    flex: 1,
    gap: spacing.xl,
    overflow: 'hidden',
  },
  sidebar: {
    width: 200,
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.xs,
    paddingRight: spacing.lg,
    borderRight: `1px solid ${colors.surfaceBorder}`,
    overflowY: 'auto',
  },
  sidebarTitle: {
    margin: 0,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: spacing.sm,
  },
  catBtn: {
    background: 'none',
    border: 'none',
    color: colors.textSecondary,
    cursor: 'pointer',
    padding: `${spacing.xs}px ${spacing.sm}px`,
    borderRadius: radii.md,
    fontSize: typography.sizes.md,
    textAlign: 'left',
    transition: transitions.fast,
  },
  catActive: {
    background: `${colors.cyan}18`,
    border: 'none',
    color: colors.cyan,
    cursor: 'pointer',
    padding: `${spacing.xs}px ${spacing.sm}px`,
    borderRadius: radii.md,
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    textAlign: 'left',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.lg,
    overflow: 'auto',
  },
  searchInput: {
    padding: `${spacing.sm}px ${spacing.lg}px`,
    fontSize: typography.sizes.md,
    width: '100%',
    boxSizing: 'border-box',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
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
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  cardTitle: {
    margin: 0,
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
  },
  badge: {
    flexShrink: 0,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.medium,
    color: colors.cyan,
    background: `${colors.cyan}18`,
    padding: `2px ${spacing.sm}px`,
    borderRadius: radii.round,
  },
  cardDesc: {
    margin: 0,
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    lineHeight: 1.4,
  },
  cardContent: {
    margin: 0,
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    lineHeight: 1.5,
    borderTop: `1px solid ${colors.surfaceBorder}`,
    paddingTop: spacing.sm,
  },
}
