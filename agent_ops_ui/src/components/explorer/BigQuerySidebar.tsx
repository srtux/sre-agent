/**
 * Tree view of BigQuery datasets and tables.
 * Expandable dataset nodes with table children.
 * Shows column types on hover.
 */
import { useState, useEffect, useCallback } from 'react'
import { ChevronRight, ChevronDown, Table2, Database, Columns3 } from 'lucide-react'
import { getDatasets, type DatasetInfo } from '../../api/explorer'
import { colors, spacing, radii, typography, transitions } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

interface BigQuerySidebarProps {
  projectId: string
  onTableSelect: (table: string) => void
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    ...glassCard(),
    padding: spacing.md,
    width: 260,
    minHeight: 200,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.xs,
  },
  header: {
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.bold,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: `${spacing.xs}px ${spacing.sm}px`,
    marginBottom: spacing.xs,
  },
  datasetRow: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    padding: `${spacing.sm}px ${spacing.sm}px`,
    cursor: 'pointer',
    borderRadius: radii.sm,
    color: colors.textPrimary,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    transition: transitions.fast,
    background: 'transparent',
    border: 'none',
    width: '100%',
    textAlign: 'left',
  },
  tableRow: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    padding: `${spacing.xs}px ${spacing.sm}px`,
    paddingLeft: spacing.xl + spacing.sm,
    cursor: 'pointer',
    borderRadius: radii.sm,
    color: colors.textSecondary,
    fontSize: typography.sizes.sm,
    transition: transitions.fast,
    background: 'transparent',
    border: 'none',
    width: '100%',
    textAlign: 'left',
    position: 'relative',
  },
  tooltip: {
    ...glassCard(),
    position: 'absolute',
    left: '100%',
    top: 0,
    marginLeft: spacing.sm,
    padding: spacing.sm,
    minWidth: 180,
    zIndex: 1500,
    fontSize: typography.sizes.xs,
    whiteSpace: 'nowrap',
  },
  colRow: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: spacing.md,
    padding: `2px 0`,
  },
  colName: {
    color: colors.textPrimary,
    fontFamily: typography.monoFamily,
  },
  colType: {
    color: colors.cyan,
    fontFamily: typography.monoFamily,
  },
  loading: {
    color: colors.textMuted,
    fontSize: typography.sizes.sm,
    padding: spacing.md,
    textAlign: 'center',
  },
  empty: {
    color: colors.textDisabled,
    fontSize: typography.sizes.sm,
    padding: spacing.md,
    textAlign: 'center',
  },
}

export default function BigQuerySidebar({
  projectId,
  onTableSelect,
}: BigQuerySidebarProps) {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [hoveredTable, setHoveredTable] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getDatasets(projectId).then((data) => {
      if (!cancelled) {
        setDatasets(data)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [projectId])

  const toggleDataset = useCallback((name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }, [])

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Datasets</div>
        <div style={styles.loading}>Loading schemas...</div>
      </div>
    )
  }

  if (datasets.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Datasets</div>
        <div style={styles.empty}>No datasets found</div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <Database size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
        Datasets
      </div>
      {datasets.map((ds) => {
        const isExpanded = expanded.has(ds.name)
        return (
          <div key={ds.name}>
            <button
              type="button"
              style={styles.datasetRow}
              onClick={() => toggleDataset(ds.name)}
              onMouseEnter={(e) => {
                ;(e.currentTarget as HTMLElement).style.background = colors.cardHover
              }}
              onMouseLeave={(e) => {
                ;(e.currentTarget as HTMLElement).style.background = 'transparent'
              }}
            >
              {isExpanded ? (
                <ChevronDown size={14} color={colors.textMuted} />
              ) : (
                <ChevronRight size={14} color={colors.textMuted} />
              )}
              <Database size={14} color={colors.primary} />
              {ds.name}
              <span style={{ color: colors.textMuted, marginLeft: 'auto', fontSize: typography.sizes.xs }}>
                {ds.tables.length}
              </span>
            </button>
            {isExpanded &&
              ds.tables.map((tbl) => {
                const fullName = `${ds.name}.${tbl.name}`
                const isHovered = hoveredTable === fullName
                return (
                  <button
                    key={fullName}
                    type="button"
                    style={styles.tableRow}
                    onClick={() => onTableSelect(fullName)}
                    onMouseEnter={(e) => {
                      ;(e.currentTarget as HTMLElement).style.background =
                        colors.cardHover
                      setHoveredTable(fullName)
                    }}
                    onMouseLeave={(e) => {
                      ;(e.currentTarget as HTMLElement).style.background =
                        'transparent'
                      setHoveredTable(null)
                    }}
                  >
                    <Table2 size={13} color={colors.cyan} />
                    {tbl.name}
                    {/* Column tooltip on hover */}
                    {isHovered && tbl.columns && tbl.columns.length > 0 && (
                      <div style={styles.tooltip}>
                        <div
                          style={{
                            fontWeight: typography.weights.semibold,
                            color: colors.textPrimary,
                            marginBottom: 4,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <Columns3 size={11} />
                          Columns
                        </div>
                        {tbl.columns.map((col) => (
                          <div key={col.name} style={styles.colRow}>
                            <span style={styles.colName}>{col.name}</span>
                            <span style={styles.colType}>{col.type}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </button>
                )
              })}
          </div>
        )
      })}
    </div>
  )
}
