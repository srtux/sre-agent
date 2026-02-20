/* eslint-disable react-refresh/only-export-components */
import type { TimeSeriesPoint, ViewMode } from '../types'

const SPARK_W = 160
const SPARK_H = 24

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

/** Extract the numeric series for a given view mode. */
export function extractSparkSeries(
  points: TimeSeriesPoint[],
  viewMode: ViewMode,
): number[] {
  switch (viewMode) {
    case 'topology':
      // Error rate: errorCount / callCount (0-1)
      return points.map((p) =>
        p.callCount > 0 ? p.errorCount / p.callCount : 0,
      )
    case 'cost':
      return points.map((p) => p.totalTokens)
    case 'latency':
      return points.map((p) => p.avgDurationMs)
  }
}

/** Trend label for the side-panel heading. */
export function sparkLabel(viewMode: ViewMode): string {
  switch (viewMode) {
    case 'topology':
      return 'Error Rate Trend'
    case 'cost':
      return 'Token Usage Trend'
    case 'latency':
      return 'Latency Trend'
  }
}

export { SPARK_H }

interface SparklineProps {
  points: number[]
  color: string
  width?: number
  height?: number
}

/** Inline SVG polyline sparkline. */
export default function Sparkline({
  points,
  color,
  width = SPARK_W,
  height = SPARK_H,
}: SparklineProps) {
  if (points.length < 2) return null

  const max = Math.max(...points) || 1
  const min = Math.min(...points)
  const range = max - min || 1

  const pad = 2
  const innerW = width - pad * 2
  const innerH = height - pad * 2

  const coords = points.map((v, i) => {
    const x = pad + (i / (points.length - 1)) * innerW
    const y = pad + innerH - ((v - min) / range) * innerH
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ display: 'block', marginTop: '2px' }}
    >
      <polyline
        points={coords.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}
