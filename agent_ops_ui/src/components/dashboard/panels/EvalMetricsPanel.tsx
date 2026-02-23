import { useMemo } from 'react'
import type { EChartsOption } from 'echarts'
import EChartWrapper from '../../charts/EChartWrapper'
import { useEvalMetrics } from '../../../hooks/useEvalMetrics'
import type { EvalMetricPoint } from '../../../types'

/** Colour palette per metric – deterministic mapping. */
const METRIC_COLORS: Record<string, string> = {
  coherence: '#06B6D4',
  groundedness: '#8B5CF6',
  fluency: '#10B981',
  safety: '#F59E0B',
  relevance: '#EC4899',
  faithfulness: '#3B82F6',
}

function colorForMetric(name: string): string {
  const lower = name.toLowerCase()
  return METRIC_COLORS[lower] ?? '#94A3B8'
}

function formatTimestamp(iso: string, hours: number): string {
  const date = new Date(iso)
  if (hours <= 24) {
    return date.toLocaleString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  }
  return date.toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })
}

export default function EvalMetricsPanel({ hours }: { hours: number }) {
  const { data, isLoading } = useEvalMetrics(hours)

  const option = useMemo((): EChartsOption => {
    if (!data || data.length === 0) return { series: [] }

    // Group data by metric name
    const byMetric: Record<string, EvalMetricPoint[]> = {}
    for (const point of data) {
      if (!byMetric[point.metricName]) {
        byMetric[point.metricName] = []
      }
      byMetric[point.metricName].push(point)
    }

    // Collect all unique time buckets for x-axis
    const allBuckets = [...new Set(data.map(p => p.timeBucket))].sort()

    // Build series per metric
    const series = Object.entries(byMetric).map(([metricName, points]) => {
      const pointMap = new Map(points.map(p => [p.timeBucket, p.avgScore]))
      return {
        name: metricName.charAt(0).toUpperCase() + metricName.slice(1),
        type: 'line' as const,
        smooth: true,
        data: allBuckets.map(b => pointMap.get(b) ?? null),
        itemStyle: { color: colorForMetric(metricName) },
        lineStyle: { width: 2, color: colorForMetric(metricName) },
        symbol: 'circle',
        symbolSize: 4,
      }
    })

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: unknown) => {
          if (!Array.isArray(params)) return ''
          let header = ''
          const lines: string[] = []
          for (const p of params) {
            const param = p as { axisValueLabel?: string; marker?: string; seriesName?: string; value?: number | null }
            if (!header && param.axisValueLabel) header = param.axisValueLabel
            if (param.value != null) {
              lines.push(`${param.marker} ${param.seriesName}: <strong>${(param.value as number).toFixed(3)}</strong>`)
            }
          }
          return `<div style="font-size:12px">${header}<br/>${lines.join('<br/>')}</div>`
        },
      },
      legend: { top: 0, right: 0 },
      xAxis: {
        type: 'category',
        data: allBuckets.map(b => formatTimestamp(b, hours)),
        axisLabel: { rotate: 0 },
      },
      yAxis: {
        type: 'value',
        name: 'Score',
        min: 0,
        max: 1,
        axisLabel: {
          formatter: (value: number) => value.toFixed(1),
        },
      },
      series,
    }
  }, [data, hours])

  return (
    <div style={{ background: '#1E293B', border: '1px solid #334155', borderRadius: '8px', padding: '16px' }}>
      <div style={{
        fontSize: '13px',
        fontWeight: 600,
        color: '#78909C',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        marginBottom: '12px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <span style={{
          display: 'inline-block',
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: '#8B5CF6',
        }} />
        AI Evaluation Scores Over Time
      </div>
      <EChartWrapper option={option} loading={isLoading} height={300} />
    </div>
  )
}
