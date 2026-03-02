/**
 * Visual data explorer — chart the results of a query.
 * Supports line, bar, scatter, and table views.
 * Auto-detects timestamp columns for default chart type.
 */
import { useState, useMemo, useEffect } from 'react'
import { LineChart, BarChart3, ScatterChart, Table2 } from 'lucide-react'
import type { EChartsOption } from 'echarts'
import EChartWrapper from '../charts/EChartWrapper'
import SqlResultsTable from './SqlResultsTable'
import { colors, spacing, radii, typography, transitions } from '../../theme/tokens'
import { glassCard, glassButton } from '../../theme/glassStyles'

type ChartType = 'line' | 'bar' | 'scatter' | 'table'

interface VisualDataExplorerProps {
  columns: string[]
  rows: Array<Record<string, unknown>>
}

const CHART_ICONS: Record<ChartType, typeof LineChart> = {
  line: LineChart,
  bar: BarChart3,
  scatter: ScatterChart,
  table: Table2,
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    ...glassCard(),
    padding: spacing.lg,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.md,
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.md,
    flexWrap: 'wrap',
  },
  chartPicker: {
    display: 'inline-flex',
    gap: 2,
    borderRadius: radii.md,
    overflow: 'hidden',
    border: `1px solid ${colors.glassBorder}`,
  },
  chartBtn: {
    ...glassButton(),
    border: 'none',
    borderRadius: 0,
    padding: spacing.sm,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 36,
    height: 36,
    transition: transitions.fast,
  },
  chartBtnActive: {
    background: colors.cyan,
    color: '#FFFFFF',
  },
  selector: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
  },
  label: {
    fontSize: typography.sizes.sm,
    color: colors.textMuted,
    fontWeight: typography.weights.medium,
  },
  select: {
    background: 'rgba(15, 23, 42, 0.6)',
    border: `1px solid ${colors.surfaceBorder}`,
    borderRadius: radii.md,
    color: colors.textPrimary,
    padding: `${spacing.xs}px ${spacing.sm}px`,
    fontSize: typography.sizes.sm,
    outline: 'none',
  },
  chartArea: {
    minHeight: 300,
  },
}

function isTimestampColumn(col: string, rows: Array<Record<string, unknown>>): boolean {
  if (/time|date|created|updated|timestamp/i.test(col)) return true
  // Check first non-null value
  for (const row of rows) {
    const v = row[col]
    if (v === null || v === undefined) continue
    if (typeof v === 'string' && !isNaN(Date.parse(v))) return true
    break
  }
  return false
}

function isNumericColumn(rows: Array<Record<string, unknown>>, col: string): boolean {
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

export default function VisualDataExplorer({
  columns,
  rows,
}: VisualDataExplorerProps) {
  const [chartType, setChartType] = useState<ChartType>('table')
  const [xAxis, setXAxis] = useState<string>('')
  const [yAxis, setYAxis] = useState<string>('')

  // Auto-detect defaults
  const numericCols = useMemo(
    () => columns.filter((c) => isNumericColumn(rows, c)),
    [columns, rows],
  )
  const timeCols = useMemo(
    () => columns.filter((c) => isTimestampColumn(c, rows)),
    [columns, rows],
  )

  useEffect(() => {
    // Auto-suggest axis and chart type
    if (timeCols.length > 0) {
      setXAxis(timeCols[0])
      setChartType('line')
    } else if (columns.length > 0) {
      setXAxis(columns[0])
    }
    if (numericCols.length > 0) {
      // Pick first numeric that isn't the x-axis
      const candidate =
        numericCols.find((c) => c !== (timeCols[0] ?? columns[0])) ??
        numericCols[0]
      setYAxis(candidate)
      if (timeCols.length === 0 && numericCols.length === columns.length) {
        setChartType('bar')
      }
    } else if (columns.length > 1) {
      setYAxis(columns[1])
    }
  }, [columns, numericCols, timeCols])

  const chartOption = useMemo<EChartsOption>(() => {
    if (!xAxis || !yAxis || rows.length === 0) return { series: [] }

    const xData = rows.map((r) => {
      const v = r[xAxis]
      return v === null || v === undefined ? '' : String(v)
    })
    const yData = rows.map((r) => {
      const v = r[yAxis]
      return typeof v === 'number' ? v : Number(v) || 0
    })

    const isTime = isTimestampColumn(xAxis, rows)

    return {
      xAxis: {
        type: isTime ? 'time' : 'category',
        data: isTime ? undefined : xData,
      },
      yAxis: { type: 'value', name: yAxis },
      series: [
        {
          name: yAxis,
          type: chartType === 'scatter' ? 'scatter' : chartType === 'bar' ? 'bar' : 'line',
          data: isTime
            ? xData.map((x, i) => [x, yData[i]])
            : yData,
          smooth: chartType === 'line',
          symbolSize: chartType === 'scatter' ? 8 : 4,
        },
      ],
      tooltip: { trigger: 'axis' },
    }
  }, [xAxis, yAxis, rows, chartType])

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        {/* Chart type picker */}
        <div style={styles.chartPicker}>
          {(Object.keys(CHART_ICONS) as ChartType[]).map((type) => {
            const Icon = CHART_ICONS[type]
            const isActive = chartType === type
            return (
              <button
                key={type}
                type="button"
                title={type}
                style={{
                  ...styles.chartBtn,
                  ...(isActive ? styles.chartBtnActive : {}),
                }}
                onClick={() => setChartType(type)}
              >
                <Icon size={16} />
              </button>
            )
          })}
        </div>

        {/* Axis selectors (hidden for table mode) */}
        {chartType !== 'table' && (
          <>
            <div style={styles.selector}>
              <span style={styles.label}>X:</span>
              <select
                style={styles.select}
                value={xAxis}
                onChange={(e) => setXAxis(e.target.value)}
              >
                {columns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </select>
            </div>
            <div style={styles.selector}>
              <span style={styles.label}>Y:</span>
              <select
                style={styles.select}
                value={yAxis}
                onChange={(e) => setYAxis(e.target.value)}
              >
                {columns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </select>
            </div>
          </>
        )}
      </div>

      {/* Chart or table */}
      <div style={styles.chartArea}>
        {chartType === 'table' ? (
          <SqlResultsTable columns={columns} rows={rows} />
        ) : (
          <EChartWrapper option={chartOption} height={300} />
        )}
      </div>
    </div>
  )
}
