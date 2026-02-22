import { useMemo } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import VirtualizedDataTable from '../../tables/VirtualizedDataTable'
import {
  useDashboardTables,
  type AgentLogRow,
  type LogSeverity,
} from '../../../hooks/useDashboardTables'

// --- Styles ---

const styles = {
  wrapper: {
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    minHeight: 0,
  } satisfies React.CSSProperties,

  header: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#78909C',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '12px',
  } satisfies React.CSSProperties,

  error: {
    background: 'rgba(255, 82, 82, 0.08)',
    border: '1px solid rgba(255, 82, 82, 0.3)',
    borderRadius: '6px',
    color: '#FF5252',
    padding: '12px 16px',
    fontSize: '14px',
  } satisfies React.CSSProperties,
} as const

// --- Severity formatting ---

const SEVERITY_COLORS: Record<LogSeverity, string> = {
  INFO: '#06B6D4',
  WARNING: '#F59E0B',
  ERROR: '#EF4444',
  DEBUG: '#78909C',
}

function SeverityBadge({ severity }: { severity: LogSeverity }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '0.3px',
        color: SEVERITY_COLORS[severity],
        background: `${SEVERITY_COLORS[severity]}18`,
        border: `1px solid ${SEVERITY_COLORS[severity]}40`,
      }}
    >
      {severity}
    </span>
  )
}

// --- Formatters ---

function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

// --- Column definitions ---

const logColumns: ColumnDef<AgentLogRow, unknown>[] = [
  {
    accessorKey: 'timestamp',
    header: 'Timestamp',
    size: 170,
    cell: ({ getValue }) => (
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
        {formatTimestamp(getValue() as string)}
      </span>
    ),
  },
  {
    accessorKey: 'agentId',
    header: 'Agent',
    size: 150,
  },
  {
    accessorKey: 'severity',
    header: 'Severity',
    size: 100,
    cell: ({ getValue }) => <SeverityBadge severity={getValue() as LogSeverity} />,
  },
  {
    accessorKey: 'message',
    header: 'Message',
    cell: ({ getValue }) => (
      <span
        title={getValue() as string}
        style={{
          display: 'block',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: '100%',
        }}
      >
        {getValue() as string}
      </span>
    ),
  },
  {
    accessorKey: 'traceId',
    header: 'Trace ID',
    size: 140,
    cell: ({ getValue }) => (
      <span
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '11px',
          color: '#78909C',
        }}
      >
        {(getValue() as string).slice(0, 12)}...
      </span>
    ),
  },
]

// --- Component ---

export default function AgentLogsPanel({ hours }: { hours: number }) {
  const { data, isLoading, isError } = useDashboardTables(hours)

  const logData = useMemo(() => data?.agentLogs ?? [], [data?.agentLogs])

  if (isError) {
    return <div style={styles.error}>Failed to load agent logs.</div>
  }

  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>Agent Logs</div>
      <VirtualizedDataTable<AgentLogRow>
        data={logData}
        columns={logColumns}
        maxHeight={500}
        estimatedRowHeight={36}
        loading={isLoading}
        emptyMessage="No logs available"
      />
    </div>
  )
}
