import React, { useState, useEffect } from 'react'
import axios from 'axios'
import type {
  GraphFilters,
  RegistryAgent,
  RegistryTool,
  AgentRegistryResponse,
  ToolRegistryResponse,
} from '../types'

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    width: '100%',
    padding: '24px',
    boxSizing: 'border-box',
    overflowY: 'auto',
  },
  header: {
    fontSize: '24px',
    fontWeight: 600,
    marginBottom: '8px',
  },
  subtitle: {
    fontSize: '14px',
    color: '#94A3B8',
    marginBottom: '24px',
  },
  tabGroup: {
    display: 'flex',
    gap: '12px',
    marginBottom: '24px',
    borderBottom: '1px solid #334155',
    paddingBottom: '0',
  },
  tab: {
    padding: '8px 16px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    background: 'transparent',
    color: '#94A3B8',
    border: 'none',
    borderBottom: '2px solid transparent',
    transition: 'all 0.2s',
  },
  activeTab: {
    padding: '8px 16px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    background: 'transparent',
    color: '#F8FAFC',
    border: 'none',
    borderBottom: '2px solid #38BDF8',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '16px',
  },
  card: {
    background: '#1E293B',
    borderRadius: '8px',
    padding: '16px',
    border: '1px solid #334155',
    cursor: 'pointer',
    transition: 'transform 0.2s, border-color 0.2s',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '16px',
  },
  cardTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#F8FAFC',
    margin: 0,
  },
  cardSubtitle: {
    fontSize: '12px',
    color: '#94A3B8',
    marginTop: '4px',
  },
  metricGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
  },
  metric: {
    display: 'flex',
    flexDirection: 'column',
  },
  metricLabel: {
    fontSize: '11px',
    color: '#64748B',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  metricValue: {
    fontSize: '16px',
    fontWeight: 500,
    color: '#E2E8F0',
    marginTop: '2px',
  },
  error: {
    color: '#F87171',
  },
  badge: {
    background: 'rgba(56, 189, 248, 0.1)',
    color: '#38BDF8',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: 500,
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '200px',
    color: '#94A3B8',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '300px',
    border: '1px dashed #334155',
    borderRadius: '8px',
    background: 'rgba(30, 41, 59, 0.5)',
    textAlign: 'center',
    padding: '32px',
  },
}

interface Props {
  filters: GraphFilters
  onSelectAgent: (serviceName: string) => void
}

type TabMode = 'agents' | 'tools'

export default function RegistryPage({ filters, onSelectAgent }: Props) {
  const [activeTab, setActiveTab] = useState<TabMode>('agents')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [agents, setAgents] = useState<RegistryAgent[]>([])
  const [tools, setTools] = useState<RegistryTool[]>([])

  useEffect(() => {
    if (!filters.projectId) return

    let isMounted = true
    setLoading(true)
    setError(null)

    const params: Record<string, string | number> = {
      project_id: filters.projectId,
      hours: filters.hours,
    }
    if (filters.startTime) params.start_time = filters.startTime
    if (filters.endTime) params.end_time = filters.endTime

    const endpoint = activeTab === 'agents' ? '/api/v1/graph/registry/agents' : '/api/v1/graph/registry/tools'

    axios
      .get(endpoint, { params })
      .then((res) => {
        if (!isMounted) return
        if (activeTab === 'agents') {
          setAgents((res.data as AgentRegistryResponse).agents || [])
        } else {
          setTools((res.data as ToolRegistryResponse).tools || [])
        }
      })
      .catch((err) => {
        if (!isMounted) return
        setError(err?.response?.data?.detail || err.message)
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [filters, activeTab])

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
    return num.toString()
  }

  const renderAgentsList = () => {
    if (loading) return <div style={styles.loading}>Loading agents...</div>
    if (error) return <div style={{ ...styles.loading, ...styles.error }}>{error}</div>

    if (agents.length === 0) {
      return (
        <div style={styles.emptyState}>
          <h3 style={{ margin: '0 0 8px 0', color: '#F8FAFC' }}>No Agents Found</h3>
          <p style={{ margin: '0 0 16px 0', color: '#94A3B8', maxWidth: '400px' }}>
            We couldn't find any agent telemetry for this time range. Ensure your application is instrumented with the OpenTelemetry GenAI SDK and using <code>cloud.platform="gcp.agent_engine"</code>.
          </p>
        </div>
      )
    }

    return (
      <div style={styles.grid}>
        {agents.map((agent) => (
          <div
            key={`${agent.serviceName}-${agent.agentId}`}
            style={styles.card}
            onClick={() => onSelectAgent(agent.serviceName)}
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = '#38BDF8'
              e.currentTarget.style.transform = 'translateY(-2px)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = '#334155'
              e.currentTarget.style.transform = 'none'
            }}
          >
            <div style={styles.cardHeader}>
              <div>
                <h3 style={styles.cardTitle}>{agent.agentName}</h3>
                <div style={styles.cardSubtitle}>{agent.serviceName}</div>
              </div>
              <div style={styles.badge}>{agent.totalSessions} Sessions</div>
            </div>

            <div style={styles.metricGrid}>
              <div style={styles.metric}>
                <span style={styles.metricLabel}>Total Turns</span>
                <span style={styles.metricValue}>{formatNumber(agent.totalTurns)}</span>
              </div>
              <div style={styles.metric}>
                <span style={styles.metricLabel}>Tokens</span>
                <span style={styles.metricValue}>{formatNumber(agent.inputTokens + agent.outputTokens)}</span>
              </div>
              <div style={styles.metric}>
                <span style={styles.metricLabel}>Error Rate</span>
                <span style={{ ...styles.metricValue, color: agent.errorRate > 0 ? '#F87171' : '#E2E8F0' }}>
                  {(agent.errorRate * 100).toFixed(1)}%
                </span>
              </div>
              <div style={styles.metric}>
                <span style={styles.metricLabel}>P95 Latency</span>
                <span style={styles.metricValue}>{formatNumber(agent.p95DurationMs)}ms</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  const renderToolsList = () => {
    if (loading) return <div style={styles.loading}>Loading tools...</div>
    if (error) return <div style={{ ...styles.loading, ...styles.error }}>{error}</div>

    if (tools.length === 0) {
      return (
        <div style={styles.emptyState}>
          <h3 style={{ margin: '0 0 8px 0', color: '#F8FAFC' }}>No Tools Found</h3>
          <p style={{ margin: '0 0 16px 0', color: '#94A3B8', maxWidth: '400px' }}>
            We couldn't find any tool execution telemetry for this time range.
          </p>
        </div>
      )
    }

    return (
      <div style={styles.grid}>
        {tools.map((tool) => (
          <div key={`${tool.serviceName}-${tool.toolId}`} style={{ ...styles.card, cursor: 'default' }}>
            <div style={styles.cardHeader}>
              <div>
                <h3 style={styles.cardTitle}>{tool.toolName}</h3>
                <div style={styles.cardSubtitle}>{tool.serviceName}</div>
              </div>
            </div>

            <div style={styles.metricGrid}>
              <div style={styles.metric}>
                <span style={styles.metricLabel}>Executions</span>
                <span style={styles.metricValue}>{formatNumber(tool.executionCount)}</span>
              </div>
              <div style={styles.metric}>
                <span style={styles.metricLabel}>Avg Latency</span>
                <span style={styles.metricValue}>{formatNumber(tool.avgDurationMs)}ms</span>
              </div>
              <div style={styles.metric}>
                <span style={styles.metricLabel}>Error Rate</span>
                <span style={{ ...styles.metricValue, color: tool.errorRate > 0 ? '#F87171' : '#E2E8F0' }}>
                  {(tool.errorRate * 100).toFixed(1)}%
                </span>
              </div>
              <div style={styles.metric}>
                <span style={styles.metricLabel}>P95 Latency</span>
                <span style={styles.metricValue}>{formatNumber(tool.p95DurationMs)}ms</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>Agent Platform Registry</h1>
      <p style={styles.subtitle}>Discover and analyze agents and tools across your infrastructure.</p>

      <div style={styles.tabGroup}>
        <button
          style={activeTab === 'agents' ? styles.activeTab : styles.tab}
          onClick={() => setActiveTab('agents')}
        >
          Agents
        </button>
        <button
          style={activeTab === 'tools' ? styles.activeTab : styles.tab}
          onClick={() => setActiveTab('tools')}
        >
          Tools
        </button>
      </div>

      <div style={{ flex: 1, position: 'relative' }}>
        {activeTab === 'agents' ? renderAgentsList() : renderToolsList()}
      </div>
    </div>
  )
}
