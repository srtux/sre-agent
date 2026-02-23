import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type {
  GraphFilters,
  RegistryAgent,
  RegistryTool,
} from '../types'
import { useAgentContext } from '../contexts/AgentContext'
import VirtualizedDataTable from './tables/VirtualizedDataTable'
import { MessageSquare, Cpu, AlertCircle, Clock, Zap, Users, Network, Route, LayoutDashboard, List, BarChart3 } from 'lucide-react'
import type { ColumnDef } from '@tanstack/react-table'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import EvalSetupWizard from './evals/EvalSetupWizard'
import { useEvalConfigs } from '../hooks/useEvalConfigs'

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    width: '100%',
    padding: '24px',
    boxSizing: 'border-box',
    overflow: 'hidden',
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
    fontWeight: 600,
    cursor: 'pointer',
    background: 'transparent',
    color: '#38BDF8',
    border: 'none',
    borderBottom: '2px solid #38BDF8',
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '200px',
    color: '#94A3B8',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: '20px',
  },
  card: {
    background: 'rgba(30, 41, 59, 0.4)',
    backdropFilter: 'blur(10px)',
    borderRadius: '16px',
    padding: '24px',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    cursor: 'pointer',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    overflow: 'hidden',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '16px',
    zIndex: 2,
  },
  cardTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#F8FAFC',
    margin: 0,
    letterSpacing: '-0.01em',
  },
  cardSubtitle: {
    fontSize: '12px',
    color: '#64748B',
    marginTop: '2px',
    fontFamily: 'monospace',
  },
  cardDescription: {
    fontSize: '13px',
    lineHeight: '1.6',
    color: '#94A3B8',
    background: 'rgba(15, 23, 42, 0.4)',
    borderLeft: '2px solid #38BDF8',
    padding: '12px 16px',
    borderRadius: '0 12px 12px 0',
    marginBottom: '24px',
    maxHeight: '120px',
    overflowY: 'auto',
    transition: 'all 0.2s ease',
    scrollbarWidth: 'thin',
    scrollbarColor: 'rgba(56, 189, 248, 0.2) transparent',
  },
  metricGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
    marginTop: 'auto',
    zIndex: 2,
  },
  metric: {
    display: 'flex',
    flexDirection: 'column',
    background: 'rgba(15, 23, 42, 0.3)',
    padding: '10px 14px',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.02)',
    transition: 'background 0.2s',
  },
  metricLabel: {
    fontSize: '10px',
    color: '#64748B',
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
    fontWeight: 700,
    marginBottom: '6px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  metricValue: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#F1F5F9',
    fontFamily: '"JetBrains Mono", monospace',
  },
  error: {
    color: '#F87171',
    textShadow: '0 0 8px rgba(248, 113, 113, 0.2)',
  },
  badge: {
    background: 'rgba(56, 189, 248, 0.1)',
    border: '1px solid rgba(56, 189, 248, 0.2)',
    color: '#38BDF8',
    padding: '4px 10px',
    borderRadius: '20px',
    fontSize: '11px',
    fontWeight: 600,
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '300px',
    border: '1px dashed rgba(255, 255, 255, 0.05)',
    borderRadius: '16px',
    background: 'rgba(30, 41, 59, 0.2)',
    textAlign: 'center',
    padding: '32px',
    color: '#64748B',
  },
  actionContainer: {
    display: 'flex',
    gap: '10px',
    marginTop: '20px',
    paddingTop: '20px',
    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
    flexWrap: 'wrap',
  },
  actionButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: 'rgba(56, 189, 248, 0.08)',
    border: '1px solid rgba(56, 189, 248, 0.15)',
    color: '#38BDF8',
    padding: '8px 16px',
    borderRadius: '10px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
  },
};

const markdownStyles = {
  p: { margin: '0 0 10px 0' },
  h1: { fontSize: '15px', margin: '16px 0 8px 0', fontWeight: 600, color: '#F8FAFC' },
  h2: { fontSize: '14px', margin: '14px 0 6px 0', fontWeight: 600, color: '#F8FAFC' },
  h3: { fontSize: '13px', margin: '12px 0 4px 0', fontWeight: 600, color: '#F8FAFC' },
  ul: { paddingLeft: '20px', margin: '8px 0', listStyleType: 'circle' },
  ol: { paddingLeft: '20px', margin: '8px 0' },
  li: { marginBottom: '4px' },
  code: { background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontFamily: '"JetBrains Mono", monospace', color: '#38BDF8', fontSize: '12px' },
  pre: { background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', overflowX: 'auto' as const, margin: '12px 0', border: '1px solid rgba(255,255,255,0.03)' },
  a: { color: '#38BDF8', textDecoration: 'none', borderBottom: '1px dotted #38BDF8' },
};

interface Props {
  filters: GraphFilters
  mode: 'agents' | 'tools'
  onNavigate: (serviceName: string, tab: string) => void
}

export default function RegistryPage({ filters, mode, onNavigate }: Props) {
  const { availableAgents, loadingAgents, registryViewMode } = useAgentContext()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const { data: evalConfigs } = useEvalConfigs()
  const [evalWizardAgent, setEvalWizardAgent] = useState<string | null>(null)

  const renderAgentActions = (serviceName: string) => (
    <div style={styles.actionContainer} onClick={(e) => e.stopPropagation()}>
      <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'topology')}><Network size={14} /> Graph</button>
      <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'trajectory')}><Route size={14} /> Trajectory</button>
      <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'dashboard')}><LayoutDashboard size={14} /> Dashboard</button>
      <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'traces')}><List size={14} /> Traces</button>
      <button
        style={styles.actionButton}
        onClick={() => {
          const hasConfig = evalConfigs?.some(c => c.agent_name === serviceName)
          if (hasConfig) {
            onNavigate(serviceName, 'evals')
          } else {
            setEvalWizardAgent(serviceName)
          }
        }}
      >
        <BarChart3 size={14} /> Evals
      </button>
    </div>
  )

  const renderToolActions = (serviceName: string) => (
    <div style={styles.actionContainer} onClick={(e) => e.stopPropagation()}>
      <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'topology')}><Network size={14} /> Graph</button>
      <button style={styles.actionButton} onClick={() => onNavigate(serviceName, 'trajectory')}><Route size={14} /> Trajectory</button>
    </div>
  )

  const renderExpandedAgentRow = (agent: RegistryAgent) => (
    <div style={{ padding: '16px', background: 'rgba(15, 23, 42, 0.5)' }}>
      {agent.description && (
        <div style={styles.markdown}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
            p: ({ node, ...props }) => <p style={markdownStyles.p} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            h1: ({ node, ...props }) => <h1 style={markdownStyles.h1} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            h2: ({ node, ...props }) => <h2 style={markdownStyles.h2} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            h3: ({ node, ...props }) => <h3 style={markdownStyles.h3} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            ul: ({ node, ...props }) => <ul style={markdownStyles.ul} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            ol: ({ node, ...props }) => <ol style={markdownStyles.ol} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            li: ({ node, ...props }) => <li style={markdownStyles.li} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            code: ({ node, ...props }) => <code style={markdownStyles.code} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            pre: ({ node, ...props }) => <pre style={markdownStyles.pre} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            a: ({ node, ...props }) => <a style={markdownStyles.a} target="_blank" rel="noopener noreferrer" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
          }}>
            {agent.description}
          </ReactMarkdown>
        </div>
      )}
      {renderAgentActions(agent.serviceName)}
    </div>
  )

  const renderExpandedToolRow = (tool: RegistryTool) => (
    <div style={{ padding: '16px', background: 'rgba(15, 23, 42, 0.5)' }}>
      {tool.description && (
        <div style={styles.markdown}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
            p: ({ node, ...props }) => <p style={markdownStyles.p} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            h1: ({ node, ...props }) => <h1 style={markdownStyles.h1} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            h2: ({ node, ...props }) => <h2 style={markdownStyles.h2} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            h3: ({ node, ...props }) => <h3 style={markdownStyles.h3} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            ul: ({ node, ...props }) => <ul style={markdownStyles.ul} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            ol: ({ node, ...props }) => <ol style={markdownStyles.ol} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            li: ({ node, ...props }) => <li style={markdownStyles.li} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            code: ({ node, ...props }) => <code style={markdownStyles.code} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            pre: ({ node, ...props }) => <pre style={markdownStyles.pre} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
            a: ({ node, ...props }) => <a style={markdownStyles.a} target="_blank" rel="noopener noreferrer" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
          }}>
            {tool.description}
          </ReactMarkdown>
        </div>
      )}
      {renderToolActions(tool.serviceName)}
    </div>
  )

  const params: Record<string, string | number> = {
    project_id: filters.projectId,
    hours: filters.hours,
  }
  if (filters.startTime) params.start_time = filters.startTime
  if (filters.endTime) params.end_time = filters.endTime

  const endpoint = mode === 'agents' ? '/api/v1/graph/registry/agents' : '/api/v1/graph/registry/tools'

  const { data, isLoading: loading, error } = useQuery({
    queryKey: ['registry', mode, filters.projectId, filters.hours, filters.startTime, filters.endTime],
    queryFn: async () => {
      const res = await axios.get(endpoint, { params })
      return res.data
    },
    enabled: !!filters.projectId,
    staleTime: 5 * 60 * 1000,
  })

  // Extract the arrays dynamically based on current mode
  const agents: RegistryAgent[] = mode === 'agents' ? data?.agents || [] : []
  const tools: RegistryTool[] = mode === 'tools' ? data?.tools || [] : []

  const errorMessage = error instanceof Error ? error.message : (error as unknown as { response?: { data?: { detail?: string } } })?.response?.data?.detail;

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
    return num.toString()
  }

  // --- Column Definitions ---

  const agentColumns = useMemo<ColumnDef<RegistryAgent, unknown>[]>(() => [
    {
      accessorKey: 'agentName',
      header: 'Name',
      cell: (info) => (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontWeight: 500, color: '#F8FAFC' }}>{info.getValue() as string}</span>
          <span style={{ fontSize: '11px', color: '#64748B' }}>{info.row.original.serviceName}</span>
        </div>
      ),
      size: 250,
    },
    {
      accessorKey: 'totalSessions',
      header: 'Sessions',
      cell: (info) => formatNumber(info.getValue() as number),
      size: 100,
    },
    {
      accessorKey: 'totalTurns',
      header: 'Turns',
      cell: (info) => formatNumber(info.getValue() as number),
      size: 100,
    },
    {
      id: 'tokens',
      header: 'Tokens',
      accessorFn: (row) => row.inputTokens + row.outputTokens,
      cell: (info) => formatNumber(info.getValue() as number),
      size: 100,
    },
    {
      accessorKey: 'errorRate',
      header: 'Error Rate',
      cell: (info) => {
        const rate = info.getValue() as number;
        return (
          <span style={{ color: rate > 0 ? '#F87171' : '#E2E8F0' }}>
            {(rate * 100).toFixed(1)}%
          </span>
        );
      },
      size: 120,
    },
    {
      accessorKey: 'p95DurationMs',
      header: 'P95 Latency',
      cell: (info) => `${formatNumber(info.getValue() as number)}ms`,
      size: 120,
    },
  ], []);

  const toolColumns = useMemo<ColumnDef<RegistryTool, unknown>[]>(() => [
    {
      accessorKey: 'toolName',
      header: 'Name',
      cell: (info) => (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontWeight: 500, color: '#F8FAFC' }}>{info.getValue() as string}</span>
          <span style={{ fontSize: '11px', color: '#64748B' }}>{info.row.original.serviceName}</span>
        </div>
      ),
      size: 250,
    },
    {
      accessorKey: 'executionCount',
      header: 'Executions',
      cell: (info) => formatNumber(info.getValue() as number),
      size: 120,
    },
    {
      accessorKey: 'errorRate',
      header: 'Error Rate',
      cell: (info) => {
        const rate = info.getValue() as number;
        return (
          <span style={{ color: rate > 0 ? '#F87171' : '#E2E8F0' }}>
            {(rate * 100).toFixed(1)}%
          </span>
        );
      },
      size: 120,
    },
    {
      accessorKey: 'avgDurationMs',
      header: 'Avg Latency',
      cell: (info) => `${formatNumber(info.getValue() as number)}ms`,
      size: 120,
    },
    {
      accessorKey: 'p95DurationMs',
      header: 'P95 Latency',
      cell: (info) => `${formatNumber(info.getValue() as number)}ms`,
      size: 120,
    },
  ], []);

  const renderAgentsList = () => {
    if (!filters.projectId) {
      return (
        <div style={styles.emptyState}>
          <h3 style={{ margin: '0 0 8px 0', color: '#F8FAFC' }}>No Project Selected</h3>
          <p style={{ margin: '0', color: '#94A3B8', maxWidth: '400px' }}>
            Enter a project ID in the toolbar and click Load to visualize agents.
          </p>
        </div>
      )
    }

    if (loading || loadingAgents) return <div style={styles.loading}>Loading agents...</div>
    if (error) return <div style={{ ...styles.loading, ...styles.error }}>{errorMessage}</div>

    if (agents.length === 0) {
      if (availableAgents.length > 0) {
        return (
          <div style={styles.emptyState}>
            <h3 style={{ margin: '0 0 8px 0', color: '#F8FAFC' }}>No Agents Found</h3>
            <p style={{ margin: '0 0 16px 0', color: '#94A3B8', maxWidth: '400px' }}>
              We couldn't find any agent telemetry for this time range. Try expanding your time window (e.g. to Last 7 days).
            </p>
          </div>
        )
      } else {
        return (
          <div style={styles.emptyState}>
            <h3 style={{ margin: '0 0 8px 0', color: '#F8FAFC' }}>No Agents Found</h3>
            <p style={{ margin: '0 0 16px 0', color: '#94A3B8', maxWidth: '400px' }}>
              We couldn't find any agent telemetry for this time range. Ensure your application is instrumented with the OpenTelemetry GenAI SDK and using <code>cloud.platform="gcp.agent_engine"</code>.
            </p>
          </div>
        )
      }
    }

    if (registryViewMode === 'table') {
      return (
        <VirtualizedDataTable
          data={agents}
          columns={agentColumns}
          onRowClick={(row) => setExpandedId(expandedId === row.serviceName ? null : row.serviceName)}
          enableSearch={true}
          searchPlaceholder="Search agents..."
          fullHeight={true}
          estimatedRowHeight={50}
          expandedRowId={expandedId}
          getRowId={(row) => row.serviceName}
          renderExpandedRow={renderExpandedAgentRow}
        />
      );
    }

    return (
      <div style={styles.grid}>
        {agents.map((agent) => (
          <div
            key={`${agent.serviceName}-${agent.agentId}`}
            style={styles.card}
            onClick={() => setExpandedId(expandedId === agent.serviceName ? null : agent.serviceName)}
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = '#38BDF8'
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = '0 12px 30px -10px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.15)'
              const desc = e.currentTarget.querySelector('.desc-box') as HTMLElement;
              if (desc) {
                desc.style.background = 'rgba(56, 189, 248, 0.05)';
                desc.style.borderColor = '#38BDF8';
              }
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = '#334155'
              e.currentTarget.style.transform = 'none'
              e.currentTarget.style.boxShadow = 'none'
              const desc = e.currentTarget.querySelector('.desc-box') as HTMLElement;
              if (desc) {
                desc.style.background = 'rgba(2, 6, 23, 0.4)';
                desc.style.borderColor = '#38BDF8';
              }
            }}
          >
            <div style={styles.cardHeader}>
              <div>
                <h3 style={styles.cardTitle}>{agent.agentName}</h3>
                <div style={styles.cardSubtitle}>{agent.serviceName}</div>
              </div>
              <div style={styles.badge}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Users size={12} />
                  <span>{agent.totalSessions} Sessions</span>
                </div>
              </div>
            </div>

            {expandedId === agent.serviceName && (
              <>
                {agent.description ? (
                  <div
                    className="desc-box"
                    style={styles.cardDescription}
                    title={agent.description}
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                      p: ({ node, ...props }) => <p style={markdownStyles.p} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      h1: ({ node, ...props }) => <h1 style={markdownStyles.h1} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      h2: ({ node, ...props }) => <h2 style={markdownStyles.h2} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      h3: ({ node, ...props }) => <h3 style={markdownStyles.h3} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      ul: ({ node, ...props }) => <ul style={markdownStyles.ul} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      ol: ({ node, ...props }) => <ol style={markdownStyles.ol} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      li: ({ node, ...props }) => <li style={markdownStyles.li} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      code: ({ node, ...props }) => <code style={markdownStyles.code} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      pre: ({ node, ...props }) => <pre style={markdownStyles.pre} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      a: ({ node, ...props }) => <a style={markdownStyles.a} target="_blank" rel="noopener noreferrer" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                    }}>
                      {agent.description}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <div style={{ ...styles.cardDescription, borderLeftColor: 'transparent', background: 'transparent' }} />
                )}

                <div style={styles.metricGrid}>
                  <div style={styles.metric}>
                    <div style={styles.metricLabel}>
                      <MessageSquare size={12} color="#38BDF8" />
                      Total Turns
                    </div>
                    <span style={styles.metricValue}>{formatNumber(agent.totalTurns)}</span>
                  </div>
                  <div style={styles.metric}>
                    <div style={styles.metricLabel}>
                      <Cpu size={12} color="#38BDF8" />
                      Tokens
                    </div>
                    <span style={styles.metricValue}>{formatNumber(agent.inputTokens + agent.outputTokens)}</span>
                  </div>
                  <div style={styles.metric}>
                    <div style={styles.metricLabel}>
                      <AlertCircle size={12} color={agent.errorRate > 0 ? '#F87171' : '#64748B'} />
                      Error Rate
                    </div>
                    <span style={{ ...styles.metricValue, color: agent.errorRate > 0 ? '#F87171' : '#F1F5F9' }}>
                      {(agent.errorRate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div style={styles.metric}>
                    <div style={styles.metricLabel}>
                      <Clock size={12} color="#38BDF8" />
                      P95 Latency
                    </div>
                    <span style={styles.metricValue}>{formatNumber(agent.p95DurationMs)}ms</span>
                  </div>
                </div>

                {renderAgentActions(agent.serviceName)}
              </>
            )}
          </div>
        ))}
      </div>
    )
  }

  const renderToolsList = () => {
    if (!filters.projectId) {
      return (
        <div style={styles.emptyState}>
          <h3 style={{ margin: '0 0 8px 0', color: '#F8FAFC' }}>No Project Selected</h3>
          <p style={{ margin: '0', color: '#94A3B8', maxWidth: '400px' }}>
            Enter a project ID in the toolbar and click Load to visualize tools.
          </p>
        </div>
      )
    }

    if (loading || loadingAgents) return <div style={styles.loading}>Loading tools...</div>
    if (error) return <div style={{ ...styles.loading, ...styles.error }}>{errorMessage}</div>

    if (tools.length === 0) {
      return (
        <div style={styles.emptyState}>
          <h3 style={{ margin: '0 0 8px 0', color: '#F8FAFC' }}>No Tools Found</h3>
          <p style={{ margin: '0 0 16px 0', color: '#94A3B8', maxWidth: '400px' }}>
            {availableAgents.length > 0
              ? "We couldn't find any tool execution telemetry for this time range. Try expanding your time window."
              : "We couldn't find any tool execution telemetry for this time range."}
          </p>
        </div>
      )
    }

    if (registryViewMode === 'table') {
      return (
        <VirtualizedDataTable
          data={tools}
          columns={toolColumns}
          onRowClick={(row) => setExpandedId(expandedId === row.serviceName ? null : row.serviceName)}
          enableSearch={true}
          searchPlaceholder="Search tools..."
          fullHeight={true}
          estimatedRowHeight={50}
          expandedRowId={expandedId}
          getRowId={(row) => row.serviceName}
          renderExpandedRow={renderExpandedToolRow}
        />
      );
    }

    return (
      <div style={styles.grid}>
        {tools.map((tool) => (
          <div
            key={`${tool.serviceName}-${tool.toolId}`}
            style={styles.card}
            onClick={() => setExpandedId(expandedId === tool.serviceName ? null : tool.serviceName)}
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = '#F59E0B'
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = '0 12px 30px -10px rgba(0, 0, 0, 0.5), 0 0 20px rgba(245, 158, 11, 0.15)'
              const desc = e.currentTarget.querySelector('.desc-box') as HTMLElement;
              if (desc) {
                desc.style.background = 'rgba(245, 158, 11, 0.05)';
                desc.style.borderColor = '#F59E0B';
              }
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = '#334155'
              e.currentTarget.style.transform = 'none'
              e.currentTarget.style.boxShadow = 'none'
              const desc = e.currentTarget.querySelector('.desc-box') as HTMLElement;
              if (desc) {
                desc.style.background = 'rgba(2, 6, 23, 0.4)';
                desc.style.borderColor = '#F59E0B';
              }
            }}
          >
            <div style={styles.cardHeader}>
              <div>
                <h3 style={styles.cardTitle}>{tool.toolName}</h3>
                <div style={styles.cardSubtitle}>{tool.serviceName}</div>
              </div>
            </div>

            {expandedId === tool.serviceName && (
              <>
                {tool.description ? (
                  <div
                    className="desc-box"
                    style={{ ...styles.cardDescription, borderLeftColor: '#F59E0B' }}
                    title={tool.description}
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                      p: ({ node, ...props }) => <p style={markdownStyles.p} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      h1: ({ node, ...props }) => <h1 style={markdownStyles.h1} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      h2: ({ node, ...props }) => <h2 style={markdownStyles.h2} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      h3: ({ node, ...props }) => <h3 style={markdownStyles.h3} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      ul: ({ node, ...props }) => <ul style={markdownStyles.ul} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      ol: ({ node, ...props }) => <ol style={markdownStyles.ol} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      li: ({ node, ...props }) => <li style={markdownStyles.li} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      code: ({ node, ...props }) => <code style={markdownStyles.code} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      pre: ({ node, ...props }) => <pre style={markdownStyles.pre} {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                      a: ({ node, ...props }) => <a style={markdownStyles.a} target="_blank" rel="noopener noreferrer" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
                    }}>
                      {tool.description}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <div style={{ ...styles.cardDescription, borderLeftColor: 'transparent', background: 'transparent' }} />
                )}

                <div style={styles.metricGrid}>
                  <div style={styles.metric}>
                    <div style={styles.metricLabel}>
                      <Zap size={12} color="#F59E0B" />
                      Executions
                    </div>
                    <span style={styles.metricValue}>{formatNumber(tool.executionCount)}</span>
                  </div>
                  <div style={styles.metric}>
                    <div style={styles.metricLabel}>
                      <Clock size={12} color="#F59E0B" />
                      Avg Latency
                    </div>
                    <span style={styles.metricValue}>{formatNumber(tool.avgDurationMs)}ms</span>
                  </div>
                  <div style={styles.metric}>
                    <div style={styles.metricLabel}>
                      <AlertCircle size={12} color={tool.errorRate > 0 ? '#F87171' : '#64748B'} />
                      Error Rate
                    </div>
                    <span style={{ ...styles.metricValue, color: tool.errorRate > 0 ? '#F87171' : '#F1F5F9' }}>
                      {(tool.errorRate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div style={styles.metric}>
                    <div style={styles.metricLabel}>
                      <Clock size={12} color="#F59E0B" />
                      P95 Latency
                    </div>
                    <span style={styles.metricValue}>{formatNumber(tool.p95DurationMs)}ms</span>
                  </div>
                </div>

                {renderToolActions(tool.serviceName)}
              </>
            )}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <div style={{
        flex: 1,
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        overflowY: registryViewMode === 'table' ? 'hidden' : 'auto',
        overflowX: 'hidden'
      }}>
        {mode === 'agents' ? renderAgentsList() : renderToolsList()}
      </div>
      <EvalSetupWizard
        isOpen={evalWizardAgent !== null}
        onClose={() => setEvalWizardAgent(null)}
        initialAgentName={evalWizardAgent ?? undefined}
        onSaved={(name) => {
          setEvalWizardAgent(null)
          onNavigate(name, 'evals')
        }}
      />
    </div>
  )
}
