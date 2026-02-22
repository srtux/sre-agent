import KpiGrid from './panels/KpiGrid'
import InteractionMetricsPanel from './panels/InteractionMetricsPanel'
import ModelAndToolPanel from './panels/ModelAndToolPanel'
import AgentLogsPanel from './panels/AgentLogsPanel'

// --- Styles ---

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    minHeight: '100vh',
    background: '#0F172A',
    color: '#F0F4F8',
    fontFamily: "'Outfit', sans-serif",
    display: 'flex',
    flexDirection: 'column',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(12, 1fr)',
    gap: '16px',
    padding: '16px 24px',
    flex: 1,
  },
  // Section spans
  kpis: { gridColumn: '1 / -1' },
  fullWidth: { gridColumn: '1 / -1' },
}

// --- Main dashboard ---

export default function AgentDashboard({ hours }: { hours: number }) {
  return (
    <div style={styles.wrapper}>
      <div style={styles.grid}>
          {/* Row 1: KPIs */}
          <div style={styles.kpis}>
          <KpiGrid hours={hours} />
          </div>

          {/* Row 2: Interactions & Metrics (charts) */}
          <div style={styles.fullWidth}>
          <InteractionMetricsPanel hours={hours} />
          </div>

          {/* Row 3: Model & Tool Stats (side-by-side tables) */}
          <div style={styles.fullWidth}>
          <ModelAndToolPanel hours={hours} />
          </div>

          {/* Row 4: Agent Logs (full-width) */}
          <div style={{ ...styles.fullWidth, minHeight: '300px', display: 'flex', flexDirection: 'column' }}>
          <AgentLogsPanel hours={hours} />
          </div>
        </div>
    </div>
  )
}
