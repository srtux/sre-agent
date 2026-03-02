import { useState } from 'react'
import {
  useCustomDashboards,
  useCreateDashboard,
  useDeleteDashboard,
} from '../hooks/useCustomDashboards'
import { colors, spacing, radii, typography, transitions } from '../theme/tokens'
import { glassCard, glassInput, primaryButton, glassButton } from '../theme/glassStyles'
import ShimmerLoading from '../components/common/ShimmerLoading'
import ErrorBanner from '../components/common/ErrorBanner'

export default function CustomDashboardsPage() {
  const { data: dashboards, isLoading, error } = useCustomDashboards()
  const createMutation = useCreateDashboard()
  const deleteMutation = useDeleteDashboard()

  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')

  const handleCreate = () => {
    if (!newName.trim()) return
    createMutation.mutate(
      { name: newName.trim(), description: newDesc.trim() },
      {
        onSuccess: () => {
          setNewName('')
          setNewDesc('')
          setShowCreate(false)
        },
      },
    )
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Custom Dashboards</h2>
        <button
          style={{ ...primaryButton(), ...styles.createBtn }}
          onClick={() => setShowCreate(!showCreate)}
        >
          {showCreate ? 'Cancel' : 'Create Dashboard'}
        </button>
      </div>

      {showCreate && (
        <div style={{ ...glassCard(), ...styles.createForm }}>
          <input
            type="text"
            placeholder="Dashboard name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            style={{ ...glassInput(), ...styles.formInput }}
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            style={{ ...glassInput(), ...styles.formInput }}
          />
          <button
            style={{ ...primaryButton(), ...styles.submitBtn }}
            onClick={handleCreate}
            disabled={createMutation.isPending || !newName.trim()}
          >
            {createMutation.isPending ? 'Creating...' : 'Create'}
          </button>
        </div>
      )}

      {error && (
        <ErrorBanner
          message={error instanceof Error ? error.message : 'Failed to load dashboards'}
        />
      )}

      {isLoading && (
        <div style={styles.grid}>
          {Array.from({ length: 4 }).map((_, i) => (
            <ShimmerLoading key={i} height={160} borderRadius={radii.lg} />
          ))}
        </div>
      )}

      {!isLoading && (dashboards ?? []).length === 0 && (
        <p style={styles.empty}>
          No dashboards yet. Create one to get started.
        </p>
      )}

      {!isLoading && (dashboards ?? []).length > 0 && (
        <div style={styles.grid}>
          {(dashboards ?? []).map((db) => (
            <div key={db.id} style={{ ...glassCard(), ...styles.card }}>
              <h3 style={styles.cardTitle}>{db.name}</h3>
              {db.description && (
                <p style={styles.cardDesc}>{db.description}</p>
              )}
              <div style={styles.cardMeta}>
                <span style={styles.metaItem}>
                  {db.widgetCount} widget{db.widgetCount !== 1 ? 's' : ''}
                </span>
                <span style={styles.metaItem}>
                  {new Date(db.lastModified).toLocaleDateString()}
                </span>
              </div>
              <div style={styles.cardActions}>
                <button
                  style={{ ...glassButton(), ...styles.actionBtn }}
                  onClick={() => {
                    // placeholder for edit
                  }}
                >
                  Edit
                </button>
                <button
                  style={{ ...glassButton(), ...styles.deleteBtn }}
                  onClick={() => deleteMutation.mutate(db.id)}
                  disabled={deleteMutation.isPending}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
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
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    margin: 0,
    fontSize: typography.sizes.title,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
  },
  createBtn: {
    padding: `${spacing.sm}px ${spacing.xl}px`,
    fontSize: typography.sizes.md,
  },
  createForm: {
    display: 'flex',
    gap: spacing.md,
    alignItems: 'center',
    padding: spacing.lg,
    flexWrap: 'wrap',
  },
  formInput: {
    padding: `${spacing.sm}px ${spacing.md}px`,
    fontSize: typography.sizes.md,
    flex: '1 1 200px',
  },
  submitBtn: {
    padding: `${spacing.sm}px ${spacing.xl}px`,
    fontSize: typography.sizes.md,
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
    padding: spacing.xl,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.sm,
  },
  cardTitle: {
    margin: 0,
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
  },
  cardDesc: {
    margin: 0,
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    lineHeight: 1.4,
  },
  cardMeta: {
    display: 'flex',
    gap: spacing.lg,
    marginTop: spacing.xs,
  },
  metaItem: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
  },
  cardActions: {
    display: 'flex',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  actionBtn: {
    padding: `${spacing.xs}px ${spacing.lg}px`,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
  },
  deleteBtn: {
    padding: `${spacing.xs}px ${spacing.lg}px`,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.error,
    borderColor: `rgba(255, 82, 82, 0.3)`,
    transition: transitions.fast,
  },
}
