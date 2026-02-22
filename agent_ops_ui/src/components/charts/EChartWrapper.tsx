import { useRef, useCallback } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption, ECharts } from 'echarts'

// --- Dark theme defaults (matches project palette) ---

const DARK_THEME_DEFAULTS: EChartsOption = {
  backgroundColor: 'transparent',
  textStyle: {
    color: '#B0BEC5',
    fontFamily: "'Outfit', sans-serif",
    fontSize: 12,
  },
  title: {
    textStyle: { color: '#F0F4F8', fontSize: 14, fontWeight: 600 },
    subtextStyle: { color: '#78909C', fontSize: 11 },
  },
  legend: {
    textStyle: { color: '#B0BEC5', fontSize: 11 },
    pageTextStyle: { color: '#78909C' },
    pageIconColor: '#78909C',
    pageIconInactiveColor: '#334155',
  },
  tooltip: {
    backgroundColor: '#1E293B',
    borderColor: '#334155',
    borderWidth: 1,
    textStyle: { color: '#F0F4F8', fontSize: 12 },
    extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.4); border-radius: 6px;',
  },
  grid: {
    left: 48,
    right: 16,
    top: 32,
    bottom: 32,
    containLabel: false,
  },
  xAxis: {
    axisLine: { lineStyle: { color: '#334155' } },
    axisTick: { lineStyle: { color: '#334155' } },
    axisLabel: { color: '#78909C', fontSize: 11 },
    splitLine: { lineStyle: { color: '#1E293B', type: 'dashed' } },
  },
  yAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#78909C', fontSize: 11 },
    splitLine: { lineStyle: { color: '#1E293B', type: 'dashed' } },
  },
  // Default color palette — cyan accent with complementary tones
  color: [
    '#06B6D4', // cyan (primary)
    '#8B5CF6', // violet
    '#F59E0B', // amber
    '#10B981', // emerald
    '#EF4444', // red
    '#EC4899', // pink
    '#3B82F6', // blue
    '#F97316', // orange
  ],
}

/** Deep-merge two ECharts option objects (one level of nesting). */
function mergeOptions(
  defaults: EChartsOption,
  overrides: EChartsOption,
): EChartsOption {
  const result = { ...defaults }

  for (const key of Object.keys(overrides) as (keyof EChartsOption)[]) {
    const base = defaults[key]
    const over = overrides[key]

    // Merge plain objects one level deep; replace everything else
    if (
      base !== null &&
      over !== null &&
      typeof base === 'object' &&
      typeof over === 'object' &&
      !Array.isArray(base) &&
      !Array.isArray(over)
    ) {
      ;(result as Record<string, unknown>)[key] = { ...base, ...over }
    } else {
      ;(result as Record<string, unknown>)[key] = over
    }
  }

  return result
}

// --- Styles ---

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: '100%',
    position: 'relative',
  },
  loadingOverlay: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(15, 23, 42, 0.6)',
    backdropFilter: 'blur(2px)',
    borderRadius: '8px',
    zIndex: 10,
  },
  spinner: {
    width: '24px',
    height: '24px',
    border: '2px solid #334155',
    borderTopColor: '#06B6D4',
    borderRadius: '50%',
    animation: 'echart-spin 0.7s linear infinite',
  },
  empty: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#475569',
    fontSize: '13px',
  },
}

// Inject keyframe once (idempotent)
const SPIN_KEYFRAME_ID = '__echart-spin-keyframe'
if (typeof document !== 'undefined' && !document.getElementById(SPIN_KEYFRAME_ID)) {
  const style = document.createElement('style')
  style.id = SPIN_KEYFRAME_ID
  style.textContent = '@keyframes echart-spin { to { transform: rotate(360deg); } }'
  document.head.appendChild(style)
}

// --- Component ---

export interface EChartWrapperProps {
  /** ECharts option configuration. Dark theme defaults are merged underneath. */
  option: EChartsOption
  /** Chart height in pixels or CSS string. @default 300 */
  height?: number | string
  /** Show a loading overlay. @default false */
  loading?: boolean
  /** Additional CSS class on the outer container. */
  className?: string
  /** Additional inline styles on the outer container. */
  style?: React.CSSProperties
  /** Callback with the ECharts instance after init. */
  onChartReady?: (instance: ECharts) => void
}

export default function EChartWrapper({
  option,
  height = 300,
  loading = false,
  className,
  style: styleProp,
  onChartReady,
}: EChartWrapperProps) {
  const chartRef = useRef<ReactECharts | null>(null)

  const handleChartReady = useCallback(
    (instance: ECharts) => {
      onChartReady?.(instance)
    },
    [onChartReady],
  )

  const resolvedHeight = typeof height === 'number' ? `${height}px` : height
  const mergedOption = mergeOptions(DARK_THEME_DEFAULTS, option)

  // Detect empty: no series data
  const series = mergedOption.series
  const isEmpty =
    !series ||
    (Array.isArray(series) && series.length === 0) ||
    (Array.isArray(series) &&
      series.every(
        (s) =>
          !('data' in s) ||
          !s.data ||
          (Array.isArray(s.data) && s.data.length === 0),
      ))

  return (
    <div
      className={className}
      style={{ ...styles.container, height: resolvedHeight, ...styleProp }}
    >
      {isEmpty && !loading ? (
        <div style={{ ...styles.empty, height: resolvedHeight }}>
          No data available
        </div>
      ) : (
        <ReactECharts
          ref={chartRef}
          option={mergedOption}
          opts={{ renderer: 'canvas' }}
          notMerge={true}
          lazyUpdate={true}
          style={{ height: resolvedHeight, width: '100%' }}
          onChartReady={handleChartReady}
        />
      )}

      {loading && (
        <div style={styles.loadingOverlay}>
          <div style={styles.spinner} />
        </div>
      )}
    </div>
  )
}
