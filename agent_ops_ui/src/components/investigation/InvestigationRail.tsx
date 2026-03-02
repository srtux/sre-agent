/**
 * Left navigation rail — expand/collapse, category tabs, badges.
 * Ported from autosre/lib/widgets/conversation/investigation_rail.dart
 */
import { colors, typography, radii } from '../../theme/tokens'
import { useDashboardStore } from '../../stores/dashboardStore'
import type { DashboardDataType } from '../../types/sre'

const TABS: Array<{ type: DashboardDataType; label: string; icon: string }> = [
  { type: 'traces', label: 'Traces', icon: '🔍' },
  { type: 'logs', label: 'Logs', icon: '📋' },
  { type: 'metrics', label: 'Metrics', icon: '📊' },
  { type: 'alerts', label: 'Alerts', icon: '🔔' },
  { type: 'council', label: 'Council', icon: '🏛️' },
  { type: 'remediation', label: 'Remediation', icon: '🔧' },
  { type: 'analytics', label: 'Analytics', icon: '📈' },
]

const styles: Record<string, React.CSSProperties> = {
  rail: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: colors.surface,
    borderRight: `1px solid ${colors.surfaceBorder}`,
    padding: '8px 0',
    overflow: 'hidden',
  },
  tab: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 12px',
    cursor: 'pointer',
    border: 'none',
    background: 'transparent',
    color: colors.textMuted,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    transition: 'color 0.15s, background 0.15s',
    borderRadius: radii.md,
    margin: '0 4px',
    position: 'relative' as const,
    whiteSpace: 'nowrap' as const,
    overflow: 'hidden',
  },
  tabActive: {
    color: colors.textPrimary,
    background: 'rgba(99, 102, 241, 0.15)',
  },
  badge: {
    minWidth: 18,
    height: 18,
    borderRadius: radii.round,
    background: colors.primary,
    color: '#fff',
    fontSize: '10px',
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 4px',
    marginLeft: 'auto',
  },
  toggleBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
    margin: '4px',
    border: 'none',
    background: 'transparent',
    color: colors.textMuted,
    cursor: 'pointer',
    fontSize: '16px',
    borderRadius: radii.md,
  },
}

export default function InvestigationRail() {
  const activeTab = useDashboardStore((s) => s.activeTab)
  const setActiveTab = useDashboardStore((s) => s.setActiveTab)
  const isExpanded = useDashboardStore((s) => s.isRailExpanded)
  const toggleRail = useDashboardStore((s) => s.toggleRail)
  const typeCounts = useDashboardStore((s) => s.typeCounts)
  const openDashboard = useDashboardStore((s) => s.openDashboard)
  const counts = typeCounts()

  return (
    <div style={styles.rail}>
      <button
        style={styles.toggleBtn}
        onClick={toggleRail}
        title={isExpanded ? 'Collapse' : 'Expand'}
      >
        {isExpanded ? '◀' : '▶'}
      </button>

      {TABS.map(({ type, label, icon }) => (
        <button
          key={type}
          style={{
            ...styles.tab,
            ...(activeTab === type ? styles.tabActive : {}),
          }}
          onClick={() => {
            setActiveTab(type)
            openDashboard()
          }}
          title={label}
        >
          <span>{icon}</span>
          {isExpanded && <span>{label}</span>}
          {counts[type] > 0 && (
            <span style={styles.badge}>{counts[type]}</span>
          )}
        </button>
      ))}
    </div>
  )
}
