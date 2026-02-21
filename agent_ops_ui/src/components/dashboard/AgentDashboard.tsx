import { DashboardFilterProvider } from '../../contexts/DashboardFilterContext'
import DashboardToolbar from './DashboardToolbar'
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
  card: {
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
  },
  cardHeader: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#78909C',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    marginBottom: '12px',
  },
  cardBody: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#475569',
    fontSize: '13px',
  },
  // Section spans
  kpis: { gridColumn: '1 / -1' },
  interactionsLeft: { gridColumn: '1 / 7' },
  interactionsRight: { gridColumn: '7 / -1' },
  statsLeft: { gridColumn: '1 / 7' },
  statsRight: { gridColumn: '7 / -1' },
  fullWidth: { gridColumn: '1 / -1' },
}

// --- Section placeholder ---

interface SectionCardProps {
  title: string
  style?: React.CSSProperties
  children?: React.ReactNode
}

function SectionCard({ title, style, children }: SectionCardProps) {
  return (
    <div style={{ ...styles.card, ...style }}>
      <div style={styles.cardHeader}>{title}</div>
      <div style={styles.cardBody}>
        {children ?? <span>No data</span>}
      </div>
    </div>
  )
}

// --- KPI row ---

const kpiStyles: Record<string, React.CSSProperties> = {
  row: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '12px',
  },
  kpi: {
    background: '#0F172A',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  kpiLabel: {
    fontSize: '11px',
    fontWeight: 500,
    color: '#78909C',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  kpiValue: {
    fontSize: '24px',
    fontWeight: 700,
    color: '#F0F4F8',
  },
  kpiDelta: {
    fontSize: '11px',
    color: '#78909C',
  },
}

interface KpiData {
  label: string
  value: string
  delta?: string
}

const PLACEHOLDER_KPIS: KpiData[] = [
  { label: 'Total Sessions', value: '—' },
  { label: 'Avg Latency', value: '—' },
  { label: 'Error Rate', value: '—' },
  { label: 'Token Usage', value: '—' },
  { label: 'Active Agents', value: '—' },
]

function KpiRow() {
  return (
    <div style={{ ...styles.card, ...styles.kpis }}>
      <div style={styles.cardHeader}>Key Metrics</div>
      <div style={kpiStyles.row}>
        {PLACEHOLDER_KPIS.map((kpi) => (
          <div key={kpi.label} style={kpiStyles.kpi}>
            <span style={kpiStyles.kpiLabel}>{kpi.label}</span>
            <span style={kpiStyles.kpiValue}>{kpi.value}</span>
            {kpi.delta && <span style={kpiStyles.kpiDelta}>{kpi.delta}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

// --- Main dashboard ---

interface AgentDashboardProps {
  availableAgents?: string[]
  loadingAgents?: boolean
}

export default function AgentDashboard({ availableAgents = [], loadingAgents = false }: AgentDashboardProps) {
  return (
    <DashboardFilterProvider>
      <div style={styles.wrapper}>
        <DashboardToolbar
          availableAgents={availableAgents}
          loadingAgents={loadingAgents}
        />

        <div style={styles.grid}>
          {/* Row 1: KPIs */}
          <KpiRow />

          {/* Row 2: Interactions & Metrics (two large charts) */}
          <SectionCard
            title="Interactions Over Time"
            style={{ ...styles.interactionsLeft, minHeight: '280px' }}
          >
            <span>Chart placeholder — sessions &amp; errors over time</span>
          </SectionCard>

          <SectionCard
            title="Latency Distribution"
            style={{ ...styles.interactionsRight, minHeight: '280px' }}
          >
            <span>Chart placeholder — p50 / p95 / p99 latency</span>
          </SectionCard>

          {/* Row 3: Model & Tool Stats (side-by-side tables) */}
          <div style={styles.fullWidth}>
            <ModelAndToolPanel />
          </div>

          {/* Row 4: Agent Logs (full-width) */}
          <div style={{ ...styles.fullWidth, minHeight: '300px', display: 'flex', flexDirection: 'column' }}>
            <AgentLogsPanel />
          </div>
        </div>
      </div>
    </DashboardFilterProvider>
  )
}
