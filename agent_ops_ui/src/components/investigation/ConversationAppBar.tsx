/**
 * Top bar: project selector, session title, controls.
 * Ported from autosre/lib/widgets/conversation/conversation_app_bar.dart
 */
import { colors, typography } from '../../theme/tokens'
import { useSessionStore } from '../../stores/sessionStore'
import { useProjectStore } from '../../stores/projectStore'
import { useDashboardStore } from '../../stores/dashboardStore'

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '8px 16px',
    background: colors.surface,
    borderBottom: `1px solid ${colors.surfaceBorder}`,
    minHeight: 48,
  },
  title: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.textPrimary,
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  projectBadge: {
    fontSize: typography.sizes.sm,
    color: colors.cyan,
    background: 'rgba(6, 182, 212, 0.1)',
    padding: '4px 10px',
    borderRadius: 9999,
    border: '1px solid rgba(6, 182, 212, 0.3)',
    cursor: 'pointer',
  },
  iconBtn: {
    background: 'transparent',
    border: 'none',
    color: colors.textMuted,
    cursor: 'pointer',
    padding: 6,
    fontSize: '18px',
    borderRadius: 6,
    display: 'flex',
    alignItems: 'center',
  },
}

export default function ConversationAppBar() {
  const currentSessionId = useSessionStore((s) => s.currentSessionId)
  const sessions = useSessionStore((s) => s.sessions)
  const projectId = useProjectStore((s) => s.projectId)
  const toggleDashboard = useDashboardStore((s) => s.toggleDashboard)
  const hasData = useDashboardStore((s) => s.hasData)

  const currentSession = sessions.find((s) => s.id === currentSessionId)
  const title = currentSession?.title || 'New Investigation'

  return (
    <div style={styles.bar}>
      {projectId && (
        <span style={styles.projectBadge} title="Current GCP Project">
          {projectId}
        </span>
      )}
      <span style={styles.title}>{title}</span>
      {hasData() && (
        <button
          style={styles.iconBtn}
          onClick={toggleDashboard}
          title="Toggle Dashboard"
        >
          📊
        </button>
      )}
    </div>
  )
}
