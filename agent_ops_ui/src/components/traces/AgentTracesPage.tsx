/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useCallback, useMemo, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { useAgentContext } from '../../contexts/AgentContext'
import { useDashboardTables, type AgentLogRow, type AgentSessionRow, type AgentTraceRow } from '../../hooks/useDashboardTables'
import VirtualizedDataTable from '../tables/VirtualizedDataTable'
import SpanDetailsView from './SpanDetailsView'
import ContextGraphViewer from '../graph/ContextGraphViewer'
import ContextInspector from '../graph/ContextInspector'
import { SessionLogsView } from './SessionLogsView'

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    width: '100%',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    overflow: 'hidden',
  },
  headerRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 0 16px 0',
  },
  title: {
    fontSize: '20px',
    fontWeight: 600,
    color: '#F0F4F8',
    margin: 0,
  },
  tabsContainer: {
    display: 'flex',
    background: '#1E293B',
    borderRadius: '8px',
    padding: '4px',
    gap: '4px',
  },
  tabButton: {
    padding: '6px 16px',
    borderRadius: '6px',
    border: 'none',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  tabActive: {
    background: '#334155',
    color: '#06B6D4',
  },
  tabInactive: {
    background: 'transparent',
    color: '#94A3B8',
  },
  tableWrapper: {
    flex: 1,
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    zIndex: 1,
  },
  error: {
    color: '#ef4444',
    padding: '16px',
  },
  badge: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 600,
    display: 'inline-block',
  },
  badgeINFO: { background: 'rgba(56, 189, 248, 0.1)', color: '#38BDF8', border: '1px solid rgba(56, 189, 248, 0.2)' },
  badgeWARNING: { background: 'rgba(250, 204, 21, 0.1)', color: '#FACC15', border: '1px solid rgba(250, 204, 21, 0.2)' },
  badgeERROR: { background: 'rgba(248, 113, 113, 0.1)', color: '#F87171', border: '1px solid rgba(248, 113, 113, 0.2)' },
  badgeDEBUG: { background: 'rgba(148, 163, 184, 0.1)', color: '#94A3B8', border: '1px solid rgba(148, 163, 184, 0.2)' },
}

type TraceTab = 'sessions' | 'traces' | 'spans'

export default function AgentTracesPage({ hours }: { hours: number }) {
  const { serviceName } = useAgentContext()
  const [activeTab, setActiveTab] = useState<TraceTab>('sessions')
  const [sessionFilter, setSessionFilter] = useState<string | null>(null)
  const [traceFilter, setTraceFilter] = useState<string | null>(null)
  const [expandedSpanId, setExpandedSpanId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'trace' | 'log' | 'graph'>('trace')
  const [selectedGraphNodeId, setSelectedGraphNodeId] = useState<string | null>(null)
  const { data, isLoading, isError } = useDashboardTables(hours, serviceName)

  React.useEffect(() => {
    if (!sessionFilter && viewMode !== 'trace') {
      setViewMode('trace')
    }
  }, [sessionFilter, viewMode])

  const sessionData = useMemo(() => data?.agentSessions ?? [], [data?.agentSessions])
  const traceData = useMemo(() => {
    const allTraces = data?.agentTraces ?? []
    if (sessionFilter) {
      return allTraces.filter(t => t.sessionId === sessionFilter)
    }
    return allTraces
  }, [data?.agentTraces, sessionFilter])
  const spanData = useMemo(() => {
    const allSpans = data?.agentLogs ?? []
    if (traceFilter) {
      return allSpans.filter(s => s.traceId === traceFilter)
    }
    return allSpans
  }, [data?.agentLogs, traceFilter])

  const handleOpenTrace = useCallback((traceId: string) => {
    window.parent.postMessage(
      JSON.stringify({ type: 'OPEN_TRACE', traceId }),
      '*',
    )
  }, [])





  // --- Session Columns ---
  const sessionColumns = useMemo(() => {
    const baseColumns = [
      {
        accessorKey: 'timestamp',
        header: 'Started At',
        size: 160,
        cell: ({ getValue }: any) => {
          const val = getValue() as string
          if (!val) return '-'
          const d = new Date(val)
          return isNaN(d.getTime())
            ? val
            : d.toLocaleString(undefined, {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })
        },
      },
      {
        accessorKey: 'sessionId',
        header: 'Session ID',
        size: 200,
        cell: ({ row }: any) => {
          const session = row.original as AgentSessionRow
          return (
            <div
              onClick={() => {
                setSessionFilter(session.sessionId)
                setActiveTab('traces')
              }}
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '12px',
                color: '#06B6D4',
                cursor: 'pointer',
                textDecoration: 'underline',
                padding: '12px 16px',
                margin: '-12px -16px',
                width: 'calc(100% + 32px)',
                height: 'calc(100% + 24px)',
                display: 'flex',
                alignItems: 'center',
              }}
              title="Open session traces in Trace Explorer"
              onMouseOver={(e) => {
                e.currentTarget.style.background = 'rgba(6, 182, 212, 0.1)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.background = 'transparent'
              }}
            >
              {session.sessionId}
            </div>
          )
        },
      },
      {
        accessorKey: 'turns',
        header: 'Turns',
        size: 100,
      },
      {
        accessorKey: 'latencyMs',
        header: 'Latency',
        size: 120,
        cell: ({ getValue }: any) => {
          const val = getValue() as number
          return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val != null ? `${val.toFixed(0)}ms` : '-'}</span>
        }
      },
      {
        accessorKey: 'totalTokens',
        header: 'Tokens',
        size: 80,
        cell: ({ getValue }: any) => {
          const val = getValue() as number
          return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val != null ? val : '-'}</span>
        }
      },
      {
        accessorKey: 'errorCount',
        header: 'Errs',
        size: 70,
        cell: ({ getValue }: any) => {
          const errs = getValue() as number
          return (
            <span style={{ color: errs > 0 ? '#F87171' : 'inherit' }}>
              {errs != null ? errs : '-'}
            </span>
          )
        },
      },
      {
        accessorKey: 'spanCount',
        header: 'Spans',
        size: 80,
      },
      {
        accessorKey: 'llmCallCount',
        header: 'LLMs',
        size: 80,
      },
      {
        accessorKey: 'toolCallCount',
        header: 'Tools',
        size: 80,
      },
      {
        accessorKey: 'llmErrorCount',
        header: 'LLM Errs',
        size: 100,
        cell: ({ getValue }: any) => {
          const errs = getValue() as number
          return (
            <span style={{ color: errs > 0 ? '#F87171' : 'inherit' }}>
              {errs != null ? errs : '-'}
            </span>
          )
        },
      },
      {
        accessorKey: 'toolErrorCount',
        header: 'Tool Errs',
        size: 100,
        cell: ({ getValue }: any) => {
          const errs = getValue() as number
          return (
            <span style={{ color: errs > 0 ? '#F87171' : 'inherit' }}>
              {errs != null ? errs : '-'}
            </span>
          )
        },
      }
    ]

    if (serviceName === '') {
      baseColumns.push(
        {
          accessorKey: 'agentName',
          header: 'Agent Name',
          size: 150,
          cell: ({ getValue }: any) => {
            const val = getValue() as string
            return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val || '-'}</span>
          }
        },
        {
          accessorKey: 'resourceId',
          header: 'Resource ID',
          size: 300,
          cell: ({ getValue }: any) => {
            const val = getValue() as string
            return <span title={val} style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val || '-'}</span>
          }
        }
      )
    }
    return baseColumns
  }, [serviceName])

  // --- Trace Columns ---
  const traceColumns = useMemo(() => {
    const baseColumns = [
      {
        accessorKey: 'timestamp',
        header: 'Timestamp',
        size: 160,
        cell: ({ getValue }: any) => {
          const val = getValue() as string
          if (!val) return '-'
          const d = new Date(val)
          return isNaN(d.getTime())
            ? val
            : d.toLocaleString(undefined, {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })
        },
      },
      {
        accessorKey: 'traceId',
        header: 'Trace ID',
        size: 180,
        cell: ({ getValue }: any) => {
          const traceId = getValue() as string
          if (!traceId) return '-'
          return (
            <div
              onClick={(e) => {
                e.stopPropagation()
                setTraceFilter(traceId)
                setActiveTab('spans')
              }}
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '12px',
                color: '#06B6D4',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                width: '100%',
                height: '100%',
              }}
              title="Filter spans by this trace"
            >
              <span style={{ textDecoration: 'underline' }}>{traceId.slice(0, 12)}...</span>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleOpenTrace(traceId)
                }}
                style={{
                  background: 'rgba(6, 182, 212, 0.1)',
                  border: 'none',
                  color: '#06B6D4',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  borderRadius: '4px',
                  transition: 'all 0.2s',
                }}
                title="Open Waterfall in Trace Explorer"
                onMouseOver={(e) => {
                  e.currentTarget.style.color = '#F0F4F8'
                  e.currentTarget.style.background = 'rgba(6, 182, 212, 0.3)'
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.color = '#06B6D4'
                  e.currentTarget.style.background = 'rgba(6, 182, 212, 0.1)'
                }}
              >
                <ExternalLink size={14} />
              </button>
            </div>
          )
        },
      },
      {
        accessorKey: 'sessionId',
        header: 'Session ID',
        size: 180,
        cell: ({ getValue }: any) => {
          return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{getValue() as string}</span>
        }
      },
      {
        accessorKey: 'latencyMs',
        header: 'Latency',
        size: 120,
        cell: ({ getValue }: any) => {
          const val = getValue() as number
          return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val != null ? `${val.toFixed(0)}ms` : '-'}</span>
        }
      },
      {
        accessorKey: 'totalTokens',
        header: 'Tokens',
        size: 80,
        cell: ({ getValue }: any) => {
          const val = getValue() as number
          return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val != null ? val : '-'}</span>
        }
      },
      {
        accessorKey: 'errorCount',
        header: 'Errs',
        size: 70,
        cell: ({ getValue }: any) => {
          const errs = getValue() as number
          return (
            <span style={{ color: errs > 0 ? '#F87171' : 'inherit' }}>
              {errs != null ? errs : '-'}
            </span>
          )
        },
      },
      {
        accessorKey: 'spanCount',
        header: 'Spans',
        size: 80,
      },
      {
        accessorKey: 'llmCallCount',
        header: 'LLMs',
        size: 80,
      },
      {
        accessorKey: 'toolCallCount',
        header: 'Tools',
        size: 80,
      },
      {
        accessorKey: 'llmErrorCount',
        header: 'LLM Errs',
        size: 100,
        cell: ({ getValue }: any) => {
          const errs = getValue() as number
          return (
            <span style={{ color: errs > 0 ? '#F87171' : 'inherit' }}>
              {errs != null ? errs : '-'}
            </span>
          )
        },
      },
      {
        accessorKey: 'toolErrorCount',
        header: 'Tool Errs',
        size: 100,
        cell: ({ getValue }: any) => {
          const errs = getValue() as number
          return (
            <span style={{ color: errs > 0 ? '#F87171' : 'inherit' }}>
              {errs != null ? errs : '-'}
            </span>
          )
        },
      }
    ]

    if (serviceName === '') {
      baseColumns.push(
        {
          accessorKey: 'agentName',
          header: 'Agent Name',
          size: 150,
          cell: ({ getValue }: any) => {
            const val = getValue() as string
            return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val || '-'}</span>
          }
        },
        {
          accessorKey: 'resourceId',
          header: 'Resource ID',
          size: 300,
          cell: ({ getValue }: any) => {
            const val = getValue() as string
            return <span title={val} style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val || '-'}</span>
          }
        }
      )
    }
    return baseColumns
  }, [serviceName, handleOpenTrace])

  // --- Span Columns ---
  const spanColumns = useMemo(() => {
    const baseColumns = [
      {
        accessorKey: 'timestamp',
        header: 'Timestamp',
        size: 140,
        cell: ({ getValue }: any) => {
          const val = getValue() as string
          if (!val) return '-'
          const d = new Date(val)
          return isNaN(d.getTime())
            ? val
            : d.toLocaleString(undefined, {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })
        },
      },
      {
        accessorKey: 'agentId',
        header: 'Agent',
        size: 180,
        cell: ({ getValue }: any) => (
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
            {getValue() as string}
          </span>
        ),
      },
      {
        accessorKey: 'severity',
        header: 'Severity',
        size: 100,
        cell: ({ getValue }: any) => {
          const sev = getValue() as string
          const badgeStyle = styles[`badge${sev}`] || styles.badgeINFO
          return <span style={{ ...styles.badge, ...badgeStyle }}>{sev}</span>
        },
      },
      {
        accessorKey: 'message',
        header: 'Message',
        size: 400,
        cell: ({ row }: any) => {
          const msg = row.original.message as string
          const parts = msg.split('|').map((s: string) => s.trim())
          const msgPart = parts.length > 0 ? parts[0] : msg
          const isLlmSpan = msg.startsWith('LLM::')
          return (
            <div
              style={{
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
              title={msg}
            >
              <span>{msgPart}</span>
              {isLlmSpan && (
                <span
                  style={{
                    background: 'rgba(139, 92, 246, 0.15)',
                    color: '#A78BFA',
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                    borderRadius: '4px',
                    padding: '1px 5px',
                    fontSize: '10px',
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                  }}
                  title="This LLM span may have AI evaluation scores — click to expand"
                >
                  AI Eval
                </span>
              )}
            </div>
          )
        },
      },
      {
        id: 'latency',
        header: 'Latency',
        size: 100,
        accessorFn: (row: any) => {
          const msg = row.message as string || ''
          const parts = msg.split('|').map((s: string) => s.trim())
          const latencyPart = parts.find((p: string) => /^[\d.]+(ms|s)$/i.test(p))
          if (!latencyPart) return -1
          if (latencyPart.toLowerCase().endsWith('ms')) return parseFloat(latencyPart)
          if (latencyPart.toLowerCase().endsWith('s')) return parseFloat(latencyPart) * 1000
          return parseFloat(latencyPart)
        },
        cell: ({ getValue }: any) => {
          const val = getValue() as number
          return (
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
              {val === -1 ? '-' : `${val}ms`}
            </span>
          )
        },
      },
      {
        id: 'tokens',
        header: 'Tokens',
        size: 100,
        accessorFn: (row: any) => {
          const msg = row.message as string || ''
          const parts = msg.split('|').map((s: string) => s.trim())
          const tokensPart = parts.find((p: string) => p.toLowerCase().includes('tokens'))
          if (!tokensPart) return -1
          return parseInt(tokensPart.replace(/ tokens/i, ''), 10) || -1
        },
        cell: ({ getValue }: any) => {
          const val = getValue() as number
          return (
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
              {val === -1 ? '-' : val}
            </span>
          )
        },
      },
      {
        accessorKey: 'traceId',
        header: 'Trace ID',
        size: 140,
        cell: ({ getValue }: any) => {
          const traceId = getValue() as string
          if (!traceId) return '-'
          return (
            <div
              onClick={(e) => {
                e.stopPropagation()
                setTraceFilter(traceId)
                setActiveTab('spans')
              }}
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '11px',
                color: '#06B6D4',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                width: '100%',
                height: '100%',
              }}
              title="Filter spans by this trace"
            >
              <span style={{ textDecoration: 'underline' }}>{traceId.slice(0, 12)}...</span>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleOpenTrace(traceId)
                }}
                style={{
                  background: 'rgba(6, 182, 212, 0.1)',
                  border: 'none',
                  color: '#06B6D4',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  borderRadius: '4px',
                  transition: 'all 0.2s',
                }}
                title="Open Waterfall in Trace Explorer"
                onMouseOver={(e) => {
                  e.currentTarget.style.color = '#F0F4F8'
                  e.currentTarget.style.background = 'rgba(6, 182, 212, 0.3)'
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.color = '#06B6D4'
                  e.currentTarget.style.background = 'rgba(6, 182, 212, 0.1)'
                }}
              >
                <ExternalLink size={14} />
              </button>
            </div>
          )
        },
      },
    ]

    if (serviceName === '') {
      baseColumns.push(
        {
          accessorKey: 'agentName',
          header: 'Agent Name',
          size: 150,
          cell: ({ getValue }: any) => {
            const val = getValue() as string
            return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val || '-'}</span>
          }
        },
        {
          accessorKey: 'resourceId',
          header: 'Resource ID',
          size: 300,
          cell: ({ getValue }: any) => {
            const val = getValue() as string
            return <span title={val} style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val || '-'}</span>
          }
        }
      )
    }
    return baseColumns
  }, [serviceName, handleOpenTrace])

  if (isError) {
    return <div style={styles.error}>Failed to load agent traces.</div>
  }

  return (
    <div style={styles.container}>
      <div style={{ ...styles.headerRow, justifyContent: 'flex-start', gap: '16px' }}>
        <div style={styles.tabsContainer}>
          <button
            style={{ ...styles.tabButton, ...(activeTab === 'sessions' ? styles.tabActive : styles.tabInactive) }}
            onClick={() => setActiveTab('sessions')}
          >
            Sessions
          </button>
          <button
            style={{ ...styles.tabButton, ...(activeTab === 'traces' ? styles.tabActive : styles.tabInactive) }}
            onClick={() => {
              setSessionFilter(null)
              setExpandedSpanId(null)
              setActiveTab('traces')
            }}
          >
            Traces
          </button>
          <button
            style={{ ...styles.tabButton, ...(activeTab === 'spans' ? styles.tabActive : styles.tabInactive) }}
            onClick={() => {
              setExpandedSpanId(null)
              setActiveTab('spans')
            }}
          >
            Spans
          </button>
        </div>
        {activeTab === 'traces' && sessionFilter && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#94A3B8', flex: 1 }}>
            <span>Filtered by Session:</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#F0F4F8' }}>{sessionFilter}</span>
            <button
              onClick={() => { setSessionFilter(null); }}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#06B6D4',
                cursor: 'pointer',
                fontSize: '12px',
                padding: '2px 6px',
                textDecoration: 'underline'
              }}
            >
              Clear
            </button>
            <div style={{ ...styles.tabsContainer, marginLeft: 'auto' }}>
              <button
                style={{ ...styles.tabButton, ...(viewMode === 'trace' ? styles.tabActive : styles.tabInactive) }}
                onClick={() => setViewMode('trace')}
              >
                Trace View
              </button>
              <button
                style={{ ...styles.tabButton, ...(viewMode === 'log' ? styles.tabActive : styles.tabInactive) }}
                onClick={() => { setViewMode('log'); setExpandedSpanId(null); }}
              >
                Logs View
              </button>
              <button
                style={{ ...styles.tabButton, ...(viewMode === 'graph' ? styles.tabActive : styles.tabInactive) }}
                onClick={() => { setViewMode('graph'); setExpandedSpanId(null); }}
              >
                Graph View
              </button>
            </div>
          </div>
        )}
        {activeTab === 'spans' && traceFilter && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#94A3B8' }}>
            <span>Filtered by Trace:</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#F0F4F8' }}>{traceFilter}</span>
            <button
              onClick={() => {
                setTraceFilter(null)
                setExpandedSpanId(null)
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#06B6D4',
                cursor: 'pointer',
                fontSize: '12px',
                padding: '2px 6px',
                textDecoration: 'underline'
              }}
            >
              Clear
            </button>
          </div>
        )}
      </div>

      <div style={styles.tableWrapper}>
        {activeTab === 'sessions' && (
          <VirtualizedDataTable<AgentSessionRow>
            data={sessionData}
            columns={sessionColumns}
            estimatedRowHeight={36}
            loading={isLoading}
            emptyMessage="No sessions found."
            fullHeight
            enableSearch
            searchPlaceholder="Search sessions..."
          />
        )}

        {activeTab === 'traces' && viewMode === 'trace' && (
          <VirtualizedDataTable<AgentTraceRow>
            data={traceData}
            columns={traceColumns}
            estimatedRowHeight={36}
            loading={isLoading}
            emptyMessage="No traces found."
            fullHeight
            enableSearch
            searchPlaceholder="Search traces..."
          />
        )}

        {activeTab === 'traces' && viewMode === 'log' && (
          <SessionLogsView
            sessionId={sessionFilter}
            activeTab={activeTab}
            viewMode={viewMode}
          />
        )}

        {activeTab === 'traces' && viewMode === 'graph' && (
          <div style={{ width: '100%', height: '100%', position: 'relative', display: 'flex', flexDirection: 'row' }}>
            <ContextGraphViewer
              sessionId={sessionFilter}
              onNodeSelect={setSelectedGraphNodeId}
            />
            <ContextInspector
              nodeId={selectedGraphNodeId}
              sessionId={sessionFilter}
              onClose={() => setSelectedGraphNodeId(null)}
            />
          </div>
        )}

        {activeTab === 'spans' && (
          <VirtualizedDataTable<AgentLogRow>
            data={spanData}
            columns={spanColumns}
            estimatedRowHeight={36}
            loading={isLoading}
            emptyMessage="No individual spans found."
            fullHeight
            enableSearch
            searchPlaceholder="Search spans..."
            expandedRowId={expandedSpanId}
            getRowId={(row) => row.timestamp + row.traceId + row.agentId}
            onRowClick={(row) => {
              const rowId = row.timestamp + row.traceId + row.agentId
              setExpandedSpanId(prev => prev === rowId ? null : rowId)
            }}
            renderExpandedRow={(row) => {
              if (!row.traceId) return null
              const rawSpanId = row.spanId || row.traceId
              return <SpanDetailsView traceId={row.traceId} spanId={rawSpanId} />
            }}
          />
        )}
      </div>
    </div>
  )
}
