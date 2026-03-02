/**
 * SQL/query results table.
 * Uses VirtualizedDataTable for large result sets.
 * Sortable columns, numeric right-alignment, NULL styling.
 */
import { useMemo } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import VirtualizedDataTable from '../tables/VirtualizedDataTable'
import { colors, spacing, typography } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

interface SqlResultsTableProps {
  columns: string[]
  rows: Array<Record<string, unknown>>
  isLoading?: boolean
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    ...glassCard(),
    overflow: 'hidden',
  },
  header: {
    padding: `${spacing.sm}px ${spacing.lg}px`,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.bold,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    borderBottom: `1px solid ${colors.glassBorder}`,
  },
  nullValue: {
    color: colors.textDisabled,
    fontStyle: 'italic',
    fontSize: typography.sizes.sm,
  },
  numericCell: {
    fontFamily: typography.monoFamily,
    textAlign: 'right',
  },
}

function isNumericColumn(rows: Array<Record<string, unknown>>, col: string): boolean {
  // Sample first 10 non-null values
  let count = 0
  for (const row of rows) {
    if (count >= 10) break
    const val = row[col]
    if (val === null || val === undefined) continue
    if (typeof val !== 'number' && isNaN(Number(val))) return false
    count++
  }
  return count > 0
}

function formatCellValue(value: unknown, isNumeric: boolean): React.ReactNode {
  if (value === null || value === undefined) {
    return <span style={styles.nullValue}>NULL</span>
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  if (isNumeric && typeof value === 'number') {
    return value.toLocaleString()
  }
  return String(value)
}

export default function SqlResultsTable({
  columns,
  rows,
  isLoading = false,
}: SqlResultsTableProps) {
  const numericCols = useMemo(() => {
    const set = new Set<string>()
    for (const col of columns) {
      if (isNumericColumn(rows, col)) set.add(col)
    }
    return set
  }, [columns, rows])

  const tableCols = useMemo<ColumnDef<Record<string, unknown>, unknown>[]>(
    () =>
      columns.map((col) => ({
        id: col,
        accessorKey: col,
        header: col,
        cell: ({ getValue }) => {
          const val = getValue()
          const isNum = numericCols.has(col)
          return (
            <span style={isNum ? styles.numericCell : undefined}>
              {formatCellValue(val, isNum)}
            </span>
          )
        },
        size: Math.max(120, col.length * 10),
      })),
    [columns, numericCols],
  )

  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>
        Results ({rows.length.toLocaleString()} row{rows.length !== 1 ? 's' : ''})
      </div>
      <VirtualizedDataTable
        data={rows}
        columns={tableCols}
        loading={isLoading}
        maxHeight={500}
        emptyMessage="No results"
        sortable
        showFooter={false}
        style={{ border: 'none', borderRadius: 0 }}
      />
    </div>
  )
}
