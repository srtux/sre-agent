/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useMemo, useState } from 'react'
import { useDashboardTables, type AgentLogRow, type AgentSessionRow, type AgentTraceRow } from '../../hooks/useDashboardTables'
import VirtualizedDataTable from '../tables/VirtualizedDataTable'

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
  const [activeTab, setActiveTab] = useState<TraceTab>('sessions')
  const { data, isLoading, isError } = useDashboardTables(hours)

  const sessionData = useMemo(() => data?.agentSessions ?? [], [data?.agentSessions])
  const traceData = useMemo(() => data?.agentTraces ?? [], [data?.agentTraces])
  const spanData = useMemo(() => data?.agentLogs ?? [], [data?.agentLogs])

  const handleOpenTrace = (traceId: string) => {
    window.parent.postMessage(
      JSON.stringify({ type: 'OPEN_TRACE', traceId }),
      '*',
    )
  }

  const handleOpenSession = (sessionId: string) => {
    window.parent.postMessage(
      JSON.stringify({ type: 'OPEN_SESSION', sessionId }),
      '*',
    )
  }



  // --- Session Columns ---
  const sessionColumns = useMemo(
    () => [
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
            <span
              onClick={() => handleOpenSession(session.sessionId)}
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '12px',
                color: '#06B6D4',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
              title="Open session traces in Trace Explorer"
            >
              {session.sessionId}
            </span>
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
          return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val.toFixed(0)}ms</span>
        }
      },
      {
        accessorKey: 'totalTokens',
        header: 'Tokens',
        size: 120,
        cell: ({ getValue }: any) => {
          const val = getValue() as number
          return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val}</span>
        }
      },
      {
        accessorKey: 'errorCount',
        header: 'Errors',
        size: 100,
        cell: ({ getValue }: any) => {
          const errs = getValue() as number
          return (
            <span style={{ color: errs > 0 ? '#F87171' : 'inherit' }}>
              {errs}
            </span>
          )
        },
      }
    ],
    []
  )

  // --- Trace Columns ---
  const traceColumns = useMemo(
    () => [
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
          return (
            <span
              onClick={() => handleOpenTrace(traceId)}
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '12px',
                color: '#06B6D4',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
              title="Open in Trace Explorer"
            >
              {traceId.slice(0, 12)}...
            </span>
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
          return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val.toFixed(0)}ms</span>
        }
      },
      {
        accessorKey: 'totalTokens',
        header: 'Tokens',
        size: 120,
        cell: ({ getValue }: any) => {
          const val = getValue() as number
          return <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>{val}</span>
        }
      },
      {
        accessorKey: 'errorCount',
        header: 'Errors',
        size: 100,
        cell: ({ getValue }: any) => {
          const errs = getValue() as number
          return (
            <span style={{ color: errs > 0 ? '#F87171' : 'inherit' }}>
              {errs}
            </span>
          )
        },
      }
    ],
    []
  )

  // --- Span Columns ---
  const spanColumns = useMemo(
    () => [
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
          return (
            <div
              style={{
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '12px',
              }}
              title={msg}
            >
              {msgPart}
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
            <span
              onClick={() => handleOpenTrace(traceId)}
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '11px',
                color: '#06B6D4',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
              title="Open in Trace Explorer"
            >
              {traceId.slice(0, 12)}...
            </span>
          )
        },
      },
    ],
    []
  )

  if (isError) {
    return <div style={styles.error}>Failed to load agent traces.</div>
  }

  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <h2 style={styles.title}>Agent Traces</h2>

        <div style={styles.tabsContainer}>
          <button
            style={{ ...styles.tabButton, ...(activeTab === 'sessions' ? styles.tabActive : styles.tabInactive) }}
            onClick={() => setActiveTab('sessions')}
          >
            Sessions
          </button>
          <button
            style={{ ...styles.tabButton, ...(activeTab === 'traces' ? styles.tabActive : styles.tabInactive) }}
            onClick={() => setActiveTab('traces')}
          >
            Traces
          </button>
          <button
            style={{ ...styles.tabButton, ...(activeTab === 'spans' ? styles.tabActive : styles.tabInactive) }}
            onClick={() => setActiveTab('spans')}
          >
            Spans
          </button>
        </div>
      </div>

      <div style={styles.tableWrapper}>
        {activeTab === 'sessions' && (
          <VirtualizedDataTable<AgentSessionRow>
            data={sessionData}
            columns={sessionColumns}
            estimatedRowHeight={36}
            loading={isLoading}
            emptyMessage="No sessions found."
          />
        )}

        {activeTab === 'traces' && (
          <VirtualizedDataTable<AgentTraceRow>
            data={traceData}
            columns={traceColumns}
            estimatedRowHeight={36}
            loading={isLoading}
            emptyMessage="No traces found."
          />
        )}

        {activeTab === 'spans' && (
          <VirtualizedDataTable<AgentLogRow>
            data={spanData}
            columns={spanColumns}
            estimatedRowHeight={36}
            loading={isLoading}
            emptyMessage="No individual spans found."
          />
        )}
      </div>
    </div>
  )
}
