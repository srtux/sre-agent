import { useRef, useMemo, useState, useCallback } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import { ArrowUp, ArrowDown, ArrowUpDown, Search } from 'lucide-react'

// --- Styles ---

const styles = {
  wrapper: {
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  } satisfies React.CSSProperties,

  scrollContainer: {
    overflow: 'auto',
    flex: 1,
  } satisfies React.CSSProperties,

  toolbar: {
    display: 'flex',
    padding: '12px 16px',
    borderBottom: '1px solid #334155',
    background: '#1E293B',
    alignItems: 'center',
    gap: '8px',
  } satisfies React.CSSProperties,

  searchInput: {
    background: '#0F172A',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '6px 12px 6px 32px',
    color: '#F0F4F8',
    fontSize: '13px',
    width: '250px',
    outline: 'none',
  } satisfies React.CSSProperties,

  searchIcon: {
    position: 'absolute',
    left: '28px',
    color: '#78909C',
  } satisfies React.CSSProperties,

  table: {
    width: '100%',
    borderCollapse: 'collapse',
    tableLayout: 'fixed',
  } satisfies React.CSSProperties,

  thead: {
    position: 'sticky',
    top: 0,
    zIndex: 10,
    background: '#0F172A',
  } satisfies React.CSSProperties,

  th: {
    padding: '10px 12px',
    fontSize: '11px',
    fontWeight: 600,
    color: '#78909C',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    textAlign: 'left',
    borderBottom: '1px solid #334155',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    cursor: 'pointer',
  } satisfies React.CSSProperties,

  thNotSortable: {
    cursor: 'default',
  } satisfies React.CSSProperties,

  thContent: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
  } satisfies React.CSSProperties,

  td: {
    padding: '8px 12px',
    fontSize: '13px',
    color: '#F0F4F8',
    borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  } satisfies React.CSSProperties,

  rowEven: {
    background: 'transparent',
  } satisfies React.CSSProperties,

  rowOdd: {
    background: 'rgba(15, 23, 42, 0.3)',
  } satisfies React.CSSProperties,

  empty: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '32px 16px',
    color: '#475569',
    fontSize: '13px',
  } satisfies React.CSSProperties,

  loadingOverlay: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(15, 23, 42, 0.6)',
    backdropFilter: 'blur(2px)',
    zIndex: 20,
  } satisfies React.CSSProperties,

  spinner: {
    width: '20px',
    height: '20px',
    border: '2px solid #334155',
    borderTopColor: '#06B6D4',
    borderRadius: '50%',
    animation: 'vdt-spin 0.7s linear infinite',
  } satisfies React.CSSProperties,

  footer: {
    padding: '8px 12px',
    fontSize: '11px',
    color: '#78909C',
    borderTop: '1px solid #334155',
    background: '#0F172A',
    display: 'flex',
    justifyContent: 'space-between',
  } satisfies React.CSSProperties,
} as const

// Inject keyframe once
const SPIN_ID = '__vdt-spin-keyframe'
if (typeof document !== 'undefined' && !document.getElementById(SPIN_ID)) {
  const el = document.createElement('style')
  el.id = SPIN_ID
  el.textContent = '@keyframes vdt-spin { to { transform: rotate(360deg); } }'
  document.head.appendChild(el)
}

// Hover CSS injection (one-time)
const HOVER_ID = '__vdt-hover-style'
if (typeof document !== 'undefined' && !document.getElementById(HOVER_ID)) {
  const el = document.createElement('style')
  el.id = HOVER_ID
  el.textContent = `
    [data-vdt-row]:hover { background: rgba(6, 182, 212, 0.06) !important; }
    [data-vdt-row-clickable="true"] { cursor: pointer; }
  `
  document.head.appendChild(el)
}

// --- Sort indicator ---

function SortIndicator({ direction }: { direction: 'asc' | 'desc' | false }) {
  if (direction === 'asc') return <ArrowUp size={12} color="#06B6D4" />
  if (direction === 'desc') return <ArrowDown size={12} color="#06B6D4" />
  return <ArrowUpDown size={12} color="#475569" />
}

// --- Component ---

export interface VirtualizedDataTableProps<TData> {
  /** Row data array. */
  data: TData[]
  /** TanStack Table column definitions. */
  columns: ColumnDef<TData, unknown>[]
  /** Max height of the scrollable viewport in pixels. @default 500 */
  maxHeight?: number
  /** Estimated row height in pixels for the virtualizer. @default 40 */
  estimatedRowHeight?: number
  /** Show a loading overlay. @default false */
  loading?: boolean
  /** Message when data is empty. @default "No data" */
  emptyMessage?: string
  /** Show row count in footer. @default true */
  showFooter?: boolean
  /** Enable sorting. @default true */
  sortable?: boolean
  /** Additional inline styles on the outer wrapper. */
  style?: React.CSSProperties
  /** Optional row click handler. */
  onRowClick?: (row: TData) => void
  /** Enable global text search filter. @default false */
  enableSearch?: boolean
  /** Placeholder for text search input. */
  searchPlaceholder?: string
  /** Make the table fill its parent container height. @default false */
  fullHeight?: boolean
}

export default function VirtualizedDataTable<TData>({
  data,
  columns,
  maxHeight = 500,
  estimatedRowHeight = 40,
  loading = false,
  emptyMessage = 'No data',
  showFooter = true,
  sortable = true,
  style: styleProp,
  onRowClick,
  enableSearch = false,
  searchPlaceholder = 'Search...',
  fullHeight = false,
}: VirtualizedDataTableProps<TData>) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [sorting, setSorting] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState('')

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: sortable ? setSorting : undefined,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: sortable ? getSortedRowModel() : undefined,
    getFilteredRowModel: getFilteredRowModel(),
  })

  const { rows } = table.getRowModel()

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: useCallback(() => scrollRef.current, []),
    estimateSize: useCallback(() => estimatedRowHeight, [estimatedRowHeight]),
    overscan: 20,
  })

  const virtualRows = virtualizer.getVirtualItems()
  const totalSize = virtualizer.getTotalSize()

  const headerGroups = useMemo(() => table.getHeaderGroups(), [table])

  return (
    <div style={{
      ...styles.wrapper,
      height: fullHeight ? '100%' : undefined,
      maxHeight: fullHeight ? undefined : `${maxHeight}px`,
      minHeight: fullHeight ? 0 : undefined,
      flex: fullHeight ? 1 : undefined,
      position: 'relative',
      ...styleProp
    }}>
      {enableSearch && (
        <div style={styles.toolbar}>
          <Search size={16} style={styles.searchIcon} />
          <input
            type="text"
            value={globalFilter ?? ''}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder={searchPlaceholder}
            style={styles.searchInput}
          />
        </div>
      )}

      {/* Scrollable viewport */}
      <div
        ref={scrollRef}
        style={{
          ...styles.scrollContainer,
          maxHeight: fullHeight ? '100%' : `${maxHeight}px`
        }}
      >
        <table style={styles.table}>
          {/* Sticky header */}
          <thead style={styles.thead}>
            {headerGroups.map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = sortable && header.column.getCanSort()
                  const sorted = header.column.getIsSorted()
                  return (
                    <th
                      key={header.id}
                      style={{
                        ...styles.th,
                        ...(!canSort ? styles.thNotSortable : {}),
                        width:
                          header.getSize() !== 150
                            ? `${header.getSize()}px`
                            : undefined,
                      }}
                      onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                    >
                      <span style={styles.thContent}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                        {canSort && <SortIndicator direction={sorted} />}
                      </span>
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>

          {/* Virtualized body */}
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{ ...styles.td, borderBottom: 'none' }}
                >
                  <div style={styles.empty}>{emptyMessage}</div>
                </td>
              </tr>
            ) : (
              <>
                {/* Top spacer */}
                {virtualRows.length > 0 && virtualRows[0].start > 0 && (
                  <tr>
                    <td
                      colSpan={columns.length}
                      style={{ height: `${virtualRows[0].start}px`, padding: 0, border: 'none' }}
                    />
                  </tr>
                )}

                {virtualRows.map((virtualRow) => {
                  const row = rows[virtualRow.index]
                  const isOdd = virtualRow.index % 2 === 1
                  return (
                    <tr
                      key={row.id}
                      data-vdt-row=""
                      data-vdt-row-clickable={!!onRowClick}
                      data-index={virtualRow.index}
                      ref={virtualizer.measureElement}
                      style={isOdd ? styles.rowOdd : styles.rowEven}
                      onClick={() => onRowClick?.(row.original)}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} style={styles.td}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  )
                })}

                {/* Bottom spacer */}
                {virtualRows.length > 0 && (
                  <tr>
                    <td
                      colSpan={columns.length}
                      style={{
                        height: `${totalSize - (virtualRows[virtualRows.length - 1].end)}px`,
                        padding: 0,
                        border: 'none',
                      }}
                    />
                  </tr>
                )}
              </>
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      {showFooter && (
        <div style={styles.footer}>
          <span>{data.length.toLocaleString()} row{data.length !== 1 ? 's' : ''}</span>
          {sorting.length > 0 && (
            <span>
              Sorted by {sorting.map((s) => `${s.id} ${s.desc ? '↓' : '↑'}`).join(', ')}
            </span>
          )}
        </div>
      )}

      {/* Loading overlay */}
      {loading && (
        <div style={styles.loadingOverlay}>
          <div style={styles.spinner} />
        </div>
      )}
    </div>
  )
}
