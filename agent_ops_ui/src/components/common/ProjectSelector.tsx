/**
 * Compact inline element showing the current project ID.
 * Click to open ProjectSelectionDialog.
 */
import React, { useState } from 'react'
import { useProjectStore } from '../../stores/projectStore'
import { ProjectSelectionDialog } from './ProjectSelectionDialog'
import { colors, typography, spacing, transitions } from '../../theme/tokens'
import { glassButton } from '../../theme/glassStyles'

export const ProjectSelector: React.FC = () => {
  const projectId = useProjectStore((s) => s.projectId)
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <>
      <button
        style={styles.trigger}
        onClick={() => setDialogOpen(true)}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = colors.cyan
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = colors.glassBorder
        }}
      >
        <span style={styles.label}>Project</span>
        <span style={styles.value}>
          {projectId || 'Select Project'}
        </span>
        <span style={styles.chevron}>&#9662;</span>
      </button>
      {dialogOpen && (
        <ProjectSelectionDialog onClose={() => setDialogOpen(false)} />
      )}
    </>
  )
}

const styles: Record<string, React.CSSProperties> = {
  trigger: {
    ...glassButton(),
    display: 'inline-flex',
    alignItems: 'center',
    gap: spacing.sm,
    padding: `${spacing.xs + 2}px ${spacing.md}px`,
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.sm,
    maxWidth: 260,
  },
  label: {
    color: colors.textMuted,
    fontSize: typography.sizes.xs,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  value: {
    color: colors.textPrimary,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  chevron: {
    color: colors.textMuted,
    fontSize: '10px',
    marginLeft: spacing.xs,
    transition: transitions.fast,
  },
}
