import type { EChartsOption } from 'echarts'
import EChartWrapper from '../charts/EChartWrapper'
import type { HistogramBucket } from '../../types'

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#A855F7',
  error: '#F87171',
  warning: '#FACC15',
  info: '#38BDF8',
  debug: '#64748B',
}

interface LogsHistogramProps {
  buckets: HistogramBucket[]
  loading?: boolean
}

function formatBucketLabel(isoString: string): string {
  const d = new Date(isoString)
  if (isNaN(d.getTime())) return isoString
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export default function LogsHistogram({ buckets, loading }: LogsHistogramProps) {
  const categories = buckets.map((b) => formatBucketLabel(b.start))

  const severityKeys = ['critical', 'error', 'warning', 'info', 'debug'] as const
  const series = severityKeys.map((key) => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    type: 'bar' as const,
    stack: 'severity',
    data: buckets.map((b) => b[key]),
    itemStyle: { color: SEVERITY_COLORS[key] },
    emphasis: { focus: 'series' as const },
    barMaxWidth: 24,
  }))

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: {
      show: true,
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
    },
    grid: {
      left: 40,
      right: 16,
      top: 8,
      bottom: 36,
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: {
        fontSize: 10,
        interval: Math.max(0, Math.floor(categories.length / 8) - 1),
      },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
    },
    series,
  }

  return (
    <EChartWrapper
      option={option}
      height={160}
      loading={loading}
      style={{ flexShrink: 0 }}
    />
  )
}
