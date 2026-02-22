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

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: 'rgba(30, 41, 59, 0.2)',
    backdropFilter: 'blur(8px)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '16px',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  scrollContainer: {
    overflow: 'auto',
    flex: 1,
    scrollbarWidth: 'thin',
    scrollbarColor: 'rgba(56, 189, 248, 0.2) transparent',
  },
  toolbar: {
    display: 'flex',
    padding: '16px 20px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
    background: 'rgba(15, 23, 42, 0.2)',
    alignItems: 'center',
    gap: '12px',
    position: 'relative',
  },
  searchWrapper: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  },
  searchInput: {
    background: 'rgba(2, 6, 23, 0.4)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '10px',
    padding: '8px 12px 8px 36px',
    color: '#F1F5F9',
    fontSize: '14px',
    width: '300px',
    outline: 'none',
    transition: 'all 0.2s',
  },
  searchIcon: {
    position: 'absolute',
    left: '12px',
    color: '#64748B',
  },
  table: {
    borderCollapse: 'separate',
    borderSpacing: 0,
    tableLayout: 'fixed',
  },
  thead: {
    position: 'sticky',
    top: 0,
    zIndex: 10,
    background: '#0F172A',
  },
  th: {
    padding: '14px 16px',
    fontSize: '11px',
    fontWeight: 700,
    color: '#94A3B8',
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
    textAlign: 'left',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    cursor: 'pointer',
    position: 'relative',
    overflow: 'visible',
    transition: 'background 0.2s',
  },
  thNotSortable: {
    cursor: 'default',
  },
  thContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    height: '100%',
    overflow: 'hidden',
  },
  resizer: {
    position: 'absolute',
    right: 0,
    top: '25%',
    height: '50%',
    width: '1px',
    background: 'rgba(255, 255, 255, 0.15)',
    cursor: 'col-resize',
    userSelect: 'none',
    touchAction: 'none',
    zIndex: 1,
  },
  td: {
    padding: '12px 16px',
    fontSize: '14px',
    color: '#CBD5E1',
    borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    transition: 'background 0.2s',
  },
  rowEven: {
    background: 'transparent',
  },
  rowOdd: {
    background: 'rgba(255, 255, 255, 0.01)',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '64px 24px',
    color: '#64748B',
    fontSize: '14px',
    gap: '8px',
  },
  loadingOverlay: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(2, 6, 23, 0.6)',
    backdropFilter: 'blur(4px)',
    zIndex: 20,
  },
  spinner: {
    width: '28px',
    height: '28px',
    border: '3px solid rgba(56, 189, 248, 0.1)',
    borderTopColor: '#38BDF8',
    borderRadius: '50%',
    animation: 'vdt-spin 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite',
  },
  footer: {
    padding: '10px 16px',
    fontSize: '12px',
    color: '#64748B',
    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
    background: 'rgba(15, 23, 42, 0.4)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
}

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
    [data-vdt-row]:hover { background: rgba(56, 189, 248, 0.04) !important; }
    [data-vdt-row-clickable="true"] { cursor: pointer; }
    .vdt-resizer { opacity: 0; transition: opacity 0.2s; }
    th:hover { background: rgba(255, 255, 255, 0.02) !important; }
    th:hover .vdt-resizer { opacity: 1; }
    .vdt-resizer.isResizing { opacity: 1; background: #38BDF8; width: 2px; }
    input:focus { border-color: rgba(56, 189, 248, 0.5) !important; box-shadow: 0 0 10px rgba(56, 189, 248, 0.1); }
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
  /** ID of the row that is currently expanded */
  expandedRowId?: string | null
  /** Function to render the expanded content for a row */
  renderExpandedRow?: (row: TData) => React.ReactNode
  /** Function to get a unique ID for a row to match expandedRowId */
  getRowId?: (row: TData) => string
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
  expandedRowId,
  renderExpandedRow,
  getRowId,
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
    columnResizeMode: 'onChange',
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
          <div style={styles.searchWrapper}>
            <Search size={16} style={styles.searchIcon} />
            <input
              type="text"
              value={globalFilter ?? ''}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder={searchPlaceholder}
              style={styles.searchInput}
            />
          </div>
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
        <table style={{ ...styles.table, width: table.getCenterTotalSize() }}>
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
                        width: `${header.getSize()}px`,
                      }}
                    >
                      <div
                        style={styles.thContent}
                        onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                      >
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                        {canSort && <SortIndicator direction={sorted} />}
                      </div>

                      {header.column.getCanResize() && (
                        <div
                          onMouseDown={header.getResizeHandler()}
                          onTouchStart={header.getResizeHandler()}
                          className={`vdt-resizer ${header.column.getIsResizing() ? 'isResizing' : ''
                            }`}
                          style={styles.resizer}
                        />
                      )}
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>

          {/* Virtualized body */}
          {rows.length === 0 ? (
            <tbody>
              <tr>
                <td
                  colSpan={columns.length}
                  style={{ ...styles.td, borderBottom: 'none' }}
                >
                  <div style={styles.empty}>{emptyMessage}</div>
                </td>
              </tr>
            </tbody>
          ) : (
            <>
              {/* Top spacer */}
              {virtualRows.length > 0 && virtualRows[0].start > 0 && (
                  <tbody>
                  <tr>
                    <td
                      colSpan={columns.length}
                      style={{ height: `${virtualRows[0].start}px`, padding: 0, border: 'none' }}
                    />
                  </tr>
                  </tbody>
                )}

                {virtualRows.map((virtualRow) => {
                  const row = rows[virtualRow.index]
                  const isOdd = virtualRow.index % 2 === 1
                  const isExpanded = getRowId ? expandedRowId === getRowId(row.original) : false;

                  return (
                  <tbody
                    key={row.id}
                    data-index={virtualRow.index}
                    ref={virtualizer.measureElement}
                  >
                    <tr
                      data-vdt-row=""
                      data-vdt-row-clickable={!!onRowClick}
                      style={isOdd ? styles.rowOdd : styles.rowEven}
                      onClick={() => onRowClick?.(row.original)}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} style={styles.td}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                    {isExpanded && renderExpandedRow && (
                      <tr>
                        <td colSpan={columns.length} style={{ padding: 0, borderBottom: '1px solid rgba(51, 65, 85, 0.5)' }}>
                          {renderExpandedRow(row.original)}
                        </td>
                      </tr>
                    )}
                  </tbody>
                  )
                })}

                {/* Bottom spacer */}
                {virtualRows.length > 0 && (
                  <tbody>
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
                  </tbody>
              )}
            </>
          )}
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
