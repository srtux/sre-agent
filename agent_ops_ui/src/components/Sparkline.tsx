/* eslint-disable react-refresh/only-export-components */
import type { TimeSeriesPoint, ViewMode } from '../types'

const SPARK_W = 160
const SPARK_H = 16

/** Map view mode to a stroke colour. */
export function sparkColor(viewMode: ViewMode): string {
  switch (viewMode) {
    case 'topology':
      return '#f85149' // error-rate red
    case 'cost':
      return '#58a6ff' // token-count blue
    case 'latency':
      return '#d29922' // latency amber
  }
}

export interface SparkPoint {
  value: number
  label: string
}

/** Extract the numeric series and formatted label for a given view mode. */
export function extractSparkSeries(
  points: TimeSeriesPoint[],
  viewMode: ViewMode,
): SparkPoint[] {
  return points.map((p) => {
    let value = 0
    let label = ''

    // Parse time
    const date = new Date(p.bucket)
    const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' })

    switch (viewMode) {
      case 'topology':
        value = p.callCount > 0 ? p.errorCount / p.callCount : 0
        label = `${timeStr} - Error Rate: ${(value * 100).toFixed(1)}%`
        break
      case 'cost':
        value = p.totalTokens
        label = `${timeStr} - ${value} tokens`
        break
      case 'latency':
        value = p.avgDurationMs
        label = `${timeStr} - ${Math.round(value)}ms`
        break
    }
    return { value, label }
  })
}

/** Trend label for the side-panel heading. */
export function sparkLabel(viewMode: ViewMode): string {
  switch (viewMode) {
    case 'topology':
      return 'Error Rate'
    case 'cost':
      return 'Token Usage'
    case 'latency':
      return 'Latency'
  }
}

export { SPARK_H }

interface SparklineProps {
  data: SparkPoint[]
  color: string
  width?: number
  height?: number
}

/** Inline SVG bar chart sparkline. */
export default function Sparkline({
  data,
  color,
  width = SPARK_W,
  height = SPARK_H,
}: SparklineProps) {
  if (data.length < 2) return null

  const values = data.map(d => d.value)
  const max = Math.max(...values) || 1
  const min = Math.min(...values)
  const range = max - min || 1

  const pad = 2
  const innerW = width - pad * 2
  const innerH = height - pad * 2

  let gap = 2
  let barWidth = (innerW - (gap * (data.length - 1))) / data.length
  if (barWidth < 1.5) {
    gap = 1
    barWidth = (innerW - (gap * (data.length - 1))) / data.length
  }
  if (barWidth < 1) {
    gap = 0
    barWidth = innerW / data.length
  }

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ display: 'block', marginTop: '2px', marginBottom: '2px', overflow: 'visible' }}
    >
      {data.map((d, i) => {
        const x = pad + i * (barWidth + gap)
        const barHeight = Math.max(2, ((d.value - min) / range) * innerH)
        const y = pad + innerH - barHeight
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barWidth}
            height={barHeight}
            fill={color}
            opacity={0.6}
            rx={1.5}
            style={{ transition: 'opacity 0.2s', cursor: 'pointer' }}
            onMouseOver={(e) => { e.currentTarget.style.opacity = '1.0' }}
            onMouseOut={(e) => { e.currentTarget.style.opacity = '0.6' }}
          >
            <title>{d.label}</title>
          </rect>
        )
      })}
    </svg>
  )
}
