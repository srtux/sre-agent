import { useMemo } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import VirtualizedDataTable from '../../tables/VirtualizedDataTable'
import {
  useDashboardTables,
  type ModelCallRow,
  type ToolCallRow,
} from '../../../hooks/useDashboardTables'

// --- Responsive CSS injection (one-time) ---

const RESPONSIVE_ID = '__mtp-responsive-style'
if (typeof document !== 'undefined' && !document.getElementById(RESPONSIVE_ID)) {
  const el = document.createElement('style')
  el.id = RESPONSIVE_ID
  el.textContent = `
    @media (max-width: 959px) {
      [data-mtp-grid] { grid-template-columns: 1fr !important; }
    }
  `
  document.head.appendChild(el)
}

// --- Styles ---

const styles = {
  container: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '16px',
  } satisfies React.CSSProperties,

  card: {
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
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

// --- Formatters ---

function formatDuration(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${ms}ms`
}

function formatErrorRate(rate: number): React.ReactNode {
  const text = `${rate.toFixed(2)}%`
  if (rate > 5) {
    return <span style={{ color: '#EF4444', fontWeight: 600 }}>{text}</span>
  }
  return <span>{text}</span>
}

function formatNumber(n: number): string {
  return n.toLocaleString()
}

// --- Column definitions ---

const modelColumns: ColumnDef<ModelCallRow, unknown>[] = [
  {
    accessorKey: 'modelName',
    header: 'Model',
    size: 160,
  },
  {
    accessorKey: 'totalCalls',
    header: 'Calls',
    size: 90,
    cell: ({ getValue }) => formatNumber(getValue() as number),
  },
  {
    accessorKey: 'p95Duration',
    header: 'P95 Latency',
    size: 100,
    cell: ({ getValue }) => formatDuration(getValue() as number),
  },
  {
    accessorKey: 'errorRate',
    header: 'Error Rate',
    size: 100,
    cell: ({ getValue }) => formatErrorRate(getValue() as number),
  },
  {
    accessorKey: 'quotaExits',
    header: 'Quota Exits',
    size: 90,
    cell: ({ getValue }) => formatNumber(getValue() as number),
  },
  {
    accessorKey: 'tokensUsed',
    header: 'Tokens',
    size: 100,
    cell: ({ getValue }) => formatNumber(getValue() as number),
  },
]

const toolColumns: ColumnDef<ToolCallRow, unknown>[] = [
  {
    accessorKey: 'toolName',
    header: 'Tool',
    size: 200,
  },
  {
    accessorKey: 'totalCalls',
    header: 'Calls',
    size: 100,
    cell: ({ getValue }) => formatNumber(getValue() as number),
  },
  {
    accessorKey: 'p95Duration',
    header: 'P95 Latency',
    size: 110,
    cell: ({ getValue }) => formatDuration(getValue() as number),
  },
  {
    accessorKey: 'errorRate',
    header: 'Error Rate',
    size: 110,
    cell: ({ getValue }) => formatErrorRate(getValue() as number),
  },
]

// --- Component ---

export default function ModelAndToolPanel({ hours }: { hours: number }) {
  const { data, isLoading, isError } = useDashboardTables(hours)

  const modelData = useMemo(() => data?.modelCalls ?? [], [data?.modelCalls])
  const toolData = useMemo(() => data?.toolCalls ?? [], [data?.toolCalls])

  if (isError) {
    return <div style={styles.error}>Failed to load model and tool data.</div>
  }

  return (
    <div data-mtp-grid="" style={styles.container}>
      {/* Model Usage */}
      <div style={styles.card}>
        <div style={styles.header}>Model Usage</div>
        <VirtualizedDataTable<ModelCallRow>
          data={modelData}
          columns={modelColumns}
          maxHeight={400}
          loading={isLoading}
          emptyMessage="No model call data"
        />
      </div>

      {/* Tool Performance */}
      <div style={styles.card}>
        <div style={styles.header}>Tool Performance</div>
        <VirtualizedDataTable<ToolCallRow>
          data={toolData}
          columns={toolColumns}
          maxHeight={400}
          loading={isLoading}
          emptyMessage="No tool call data"
        />
      </div>
    </div>
  )
}
