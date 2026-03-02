/**
 * Main dashboard panel — right side of investigation layout.
 * Tab bar with 7 categories, count badges, and content rendering.
 */
import { colors, typography, radii, spacing } from '../../theme/tokens'
import { glassSurface } from '../../theme/glassStyles'
import { useDashboardStore } from '../../stores/dashboardStore'
import type { DashboardDataType } from '../../types/sre'

import LiveTracePanel from './panels/LiveTracePanel'
import LiveLogsExplorer from './panels/LiveLogsExplorer'
import LiveMetricsPanel from './panels/LiveMetricsPanel'
import LiveAlertsPanel from './panels/LiveAlertsPanel'
import LiveCouncilPanel from './panels/LiveCouncilPanel'
import LiveRemediationPanel from './panels/LiveRemediationPanel'
import LiveChartsPanel from './panels/LiveChartsPanel'

const TABS: Array<{ type: DashboardDataType; label: string }> = [
  { type: 'traces', label: 'Traces' },
  { type: 'logs', label: 'Logs' },
  { type: 'metrics', label: 'Metrics' },
  { type: 'alerts', label: 'Alerts' },
  { type: 'council', label: 'Council' },
  { type: 'remediation', label: 'Remediation' },
  { type: 'analytics', label: 'Analytics' },
]

const PANEL_MAP: Record<DashboardDataType, React.ComponentType> = {
  traces: LiveTracePanel,
  logs: LiveLogsExplorer,
  metrics: LiveMetricsPanel,
  alerts: LiveAlertsPanel,
  council: LiveCouncilPanel,
  remediation: LiveRemediationPanel,
  analytics: LiveChartsPanel,
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    ...glassSurface(),
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    borderBottom: `1px solid ${colors.surfaceBorder}`,
    padding: `0 ${spacing.sm}px`,
    minHeight: 44,
    flexShrink: 0,
  },
  tabBar: {
    display: 'flex',
    alignItems: 'center',
    flex: 1,
    gap: 2,
    overflow: 'auto',
  },
  tab: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: `${spacing.sm}px ${spacing.md}px`,
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    color: colors.textMuted,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    cursor: 'pointer',
    whiteSpace: 'nowrap' as const,
    transition: 'color 0.15s, border-color 0.15s',
  },
  tabActive: {
    color: colors.textPrimary,
    borderBottomColor: colors.primary,
  },
  badge: {
    minWidth: 16,
    height: 16,
    borderRadius: radii.round,
    background: colors.primary,
    color: '#fff',
    fontSize: '10px',
    fontWeight: 600,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 4px',
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    color: colors.textMuted,
    cursor: 'pointer',
    padding: spacing.sm,
    fontSize: '16px',
    borderRadius: radii.sm,
    flexShrink: 0,
  },
  content: {
    flex: 1,
    overflow: 'auto',
    padding: spacing.lg,
  },
  empty: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    minHeight: 200,
    gap: spacing.md,
    color: colors.textMuted,
    fontSize: typography.sizes.md,
  },
  emptyIcon: {
    fontSize: '32px',
    opacity: 0.4,
  },
}

export default function DashboardPanel() {
  const activeTab = useDashboardStore((s) => s.activeTab)
  const setActiveTab = useDashboardStore((s) => s.setActiveTab)
  const closeDashboard = useDashboardStore((s) => s.closeDashboard)
  const typeCounts = useDashboardStore((s) => s.typeCounts)
  const counts = typeCounts()

  const ActivePanel = PANEL_MAP[activeTab]
  const count = counts[activeTab]

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.tabBar}>
          {TABS.map(({ type, label }) => (
            <button
              key={type}
              style={{
                ...styles.tab,
                ...(activeTab === type ? styles.tabActive : {}),
              }}
              onClick={() => setActiveTab(type)}
            >
              {label}
              {counts[type] > 0 && (
                <span style={styles.badge}>{counts[type]}</span>
              )}
            </button>
          ))}
        </div>
        <button
          style={styles.closeBtn}
          onClick={closeDashboard}
          title="Close Dashboard"
        >
          ✕
        </button>
      </div>

      <div style={styles.content}>
        {count > 0 ? (
          <ActivePanel />
        ) : (
          <div style={styles.empty}>
            <span style={styles.emptyIcon}>📭</span>
            <span>No {activeTab} data yet</span>
            <span style={{ fontSize: typography.sizes.sm, color: colors.textDisabled }}>
              Data will appear here as the agent investigates
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
