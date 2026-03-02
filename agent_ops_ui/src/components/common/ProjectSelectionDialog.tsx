/**
 * Modal overlay for project selection.
 * Shows starred, recent, and search results.
 */
import React, { useState, useMemo, useEffect, useRef } from 'react'
import { useProjectStore } from '../../stores/projectStore'
import { colors, typography, spacing, radii, zIndex, shadows } from '../../theme/tokens'
import { glassCardElevated, glassInput, glassButton } from '../../theme/glassStyles'

interface Props {
  onClose: () => void
}

export const ProjectSelectionDialog: React.FC<Props> = ({ onClose }) => {
  const projectId = useProjectStore((s) => s.projectId)
  const recentProjects = useProjectStore((s) => s.recentProjects)
  const starredProjects = useProjectStore((s) => s.starredProjects)
  const setProjectId = useProjectStore((s) => s.setProjectId)
  const toggleStarred = useProjectStore((s) => s.toggleStarred)

  const [search, setSearch] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  const allProjects = useMemo(() => {
    const set = new Set([...starredProjects, ...recentProjects])
    if (projectId) set.add(projectId)
    return Array.from(set)
  }, [starredProjects, recentProjects, projectId])

  const filteredProjects = useMemo(() => {
    if (!search.trim()) return []
    const q = search.toLowerCase()
    return allProjects.filter((p) => p.toLowerCase().includes(q))
  }, [search, allProjects])

  const handleSelect = (id: string) => {
    setProjectId(id)
    onClose()
  }

  const renderProjectItem = (id: string) => {
    const isStarred = starredProjects.includes(id)
    const isActive = id === projectId
    return (
      <div
        key={id}
        style={{
          ...styles.projectItem,
          ...(isActive ? styles.projectItemActive : {}),
        }}
        onClick={() => handleSelect(id)}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = colors.cardHover
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = isActive
            ? `${colors.cyan}10`
            : 'transparent'
        }}
      >
        <button
          style={styles.starBtn}
          onClick={(e) => {
            e.stopPropagation()
            toggleStarred(id)
          }}
          title={isStarred ? 'Unstar' : 'Star'}
        >
          {isStarred ? '\u2605' : '\u2606'}
        </button>
        <span style={styles.projectId}>{id}</span>
        {isActive && <span style={styles.activeBadge}>current</span>}
      </div>
    )
  }

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.dialog} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <h2 style={styles.title}>Select Project</h2>
          <button style={styles.closeBtn} onClick={onClose}>
            &times;
          </button>
        </div>

        {/* Search */}
        <div style={styles.searchContainer}>
          <input
            ref={inputRef}
            style={styles.searchInput}
            placeholder="Search or enter project ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && search.trim()) {
                handleSelect(search.trim())
              }
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = colors.cyan
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = colors.surfaceBorder
            }}
          />
        </div>

        <div style={styles.content}>
          {/* Starred projects */}
          {starredProjects.length > 0 && !search && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Starred</h3>
              {starredProjects.map(renderProjectItem)}
            </div>
          )}

          {/* Recent projects */}
          {recentProjects.length > 0 && !search && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Recent</h3>
              {recentProjects
                .filter((p) => !starredProjects.includes(p))
                .map(renderProjectItem)}
            </div>
          )}

          {/* Search results */}
          {search && filteredProjects.length > 0 && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Results</h3>
              {filteredProjects.map(renderProjectItem)}
            </div>
          )}

          {/* Direct entry hint */}
          {search && filteredProjects.length === 0 && (
            <div style={styles.hint}>
              <p style={styles.hintText}>
                Press <strong>Enter</strong> to use &ldquo;{search}&rdquo; as
                project ID
              </p>
            </div>
          )}

          {/* Empty state */}
          {!search && recentProjects.length === 0 && starredProjects.length === 0 && (
            <p style={styles.emptyText}>
              Type a GCP project ID above to get started.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    inset: 0,
    zIndex: zIndex.modal,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0, 0, 0, 0.6)',
    backdropFilter: 'blur(4px)',
  },
  dialog: {
    ...glassCardElevated({ borderRadius: radii.xl }),
    width: 460,
    maxWidth: '92vw',
    maxHeight: '70vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: shadows.lg,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: `${spacing.lg}px ${spacing.xl}px`,
    borderBottom: `1px solid ${colors.surfaceBorder}`,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.semibold,
    fontFamily: typography.fontFamily,
    margin: 0,
  },
  closeBtn: {
    ...glassButton(),
    border: 'none',
    background: 'transparent',
    color: colors.textMuted,
    fontSize: '22px',
    cursor: 'pointer',
    padding: `${spacing.xs}px ${spacing.sm}px`,
    lineHeight: 1,
  },
  searchContainer: {
    padding: `${spacing.md}px ${spacing.xl}px`,
  },
  searchInput: {
    ...glassInput(),
    width: '100%',
    padding: `${spacing.sm + 2}px ${spacing.md}px`,
    fontSize: typography.sizes.md,
    fontFamily: typography.fontFamily,
    boxSizing: 'border-box',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: `0 ${spacing.xl}px ${spacing.lg}px`,
  },
  section: {
    marginBottom: spacing.md,
  },
  sectionTitle: {
    color: colors.textMuted,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.semibold,
    fontFamily: typography.fontFamily,
    textTransform: 'uppercase' as const,
    letterSpacing: '1px',
    margin: `${spacing.sm}px 0`,
  },
  projectItem: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    padding: `${spacing.sm}px ${spacing.md}px`,
    borderRadius: radii.md,
    cursor: 'pointer',
    transition: 'background 0.15s ease',
  },
  projectItemActive: {
    background: `${colors.cyan}10`,
  },
  starBtn: {
    background: 'transparent',
    border: 'none',
    color: colors.warning,
    cursor: 'pointer',
    fontSize: '16px',
    padding: 0,
    lineHeight: 1,
    flexShrink: 0,
  },
  projectId: {
    color: colors.textPrimary,
    fontSize: typography.sizes.sm,
    fontFamily: typography.monoFamily,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flex: 1,
  },
  activeBadge: {
    color: colors.cyan,
    fontSize: typography.sizes.xs,
    fontFamily: typography.fontFamily,
    flexShrink: 0,
  },
  hint: {
    padding: `${spacing.lg}px 0`,
    textAlign: 'center',
  },
  hintText: {
    color: colors.textSecondary,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    margin: 0,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    textAlign: 'center',
    padding: `${spacing.xl}px 0`,
  },
}
