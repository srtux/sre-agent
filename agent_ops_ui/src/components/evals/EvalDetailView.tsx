import React, { useMemo, useCallback } from 'react'
import type { EChartsOption } from 'echarts'
import type { EvalConfig, EvalMetricPoint } from '../../types'
import { useEvalMetrics } from '../../hooks/useEvalMetrics'
import EChartWrapper from '../charts/EChartWrapper'
import { ArrowLeft, Settings } from 'lucide-react'

const METRIC_COLORS: Record<string, string> = {
  coherence: '#06B6D4',
  groundedness: '#8B5CF6',
  fluency: '#10B981',
  safety: '#F59E0B',
  relevance: '#EC4899',
  faithfulness: '#3B82F6',
}

function colorForMetric(name: string): string {
  return METRIC_COLORS[name.toLowerCase()] ?? '#94A3B8'
}

function formatTimestamp(iso: string, hours: number): string {
  const date = new Date(iso)
  if (hours <= 24) {
    return date.toLocaleString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  }
  return date.toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

interface EvalDetailViewProps {
  config: EvalConfig
  hours: number
  onBack: () => void
  onEdit: (config: EvalConfig) => void
}

export default function EvalDetailView({
  config,
  hours,
  onBack,
  onEdit,
}: EvalDetailViewProps) {
  const { data, isLoading } = useEvalMetrics(hours, config.agent_name)

  const handleEdit = useCallback(() => {
    onEdit(config)
  }, [onEdit, config])

  const samplingPct = Math.round(config.sampling_rate * 100)

  const chartOption = useMemo((): EChartsOption => {
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
    const allBuckets = [...new Set(data.map((p) => p.timeBucket))].sort()

    // Build series per metric
    const series = Object.entries(byMetric).map(([metricName, points]) => {
      const pointMap = new Map(points.map((p) => [p.timeBucket, p.avgScore]))
      return {
        name: metricName.charAt(0).toUpperCase() + metricName.slice(1),
        type: 'line' as const,
        smooth: true,
        data: allBuckets.map((b) => pointMap.get(b) ?? null),
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
            const param = p as {
              axisValueLabel?: string
              marker?: string
              seriesName?: string
              value?: number | null
            }
            if (!header && param.axisValueLabel) header = param.axisValueLabel
            if (param.value != null) {
              lines.push(
                `${param.marker} ${param.seriesName}: <strong>${(param.value as number).toFixed(3)}</strong>`,
              )
            }
          }
          return `<div style="font-size:12px">${header}<br/>${lines.join('<br/>')}</div>`
        },
      },
      legend: { top: 0, right: 0 },
      xAxis: {
        type: 'category',
        data: allBuckets.map((b) => formatTimestamp(b, hours)),
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
    <div style={styles.container}>
      {/* Back button */}
      <button type="button" style={styles.backButton} onClick={onBack}>
        <ArrowLeft size={16} />
        Back to Evaluations
      </button>

      {/* Config summary bar */}
      <div style={styles.summaryBar}>
        <div style={styles.summaryLeft}>
          <span style={styles.agentName}>{config.agent_name}</span>
          <span
            style={{
              ...styles.badge,
              background: config.is_enabled
                ? 'rgba(16, 185, 129, 0.15)'
                : 'rgba(100, 116, 139, 0.15)',
              color: config.is_enabled ? '#10B981' : '#64748B',
              borderColor: config.is_enabled
                ? 'rgba(16, 185, 129, 0.3)'
                : 'rgba(100, 116, 139, 0.3)',
            }}
          >
            {config.is_enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
        <div style={styles.summaryRight}>
          <span style={styles.summaryText}>Sampling: {samplingPct}%</span>
          <span style={styles.summaryText}>
            Metrics: {config.metrics.join(', ')}
          </span>
          <button type="button" style={styles.editButton} onClick={handleEdit}>
            <Settings size={14} />
            Edit
          </button>
        </div>
      </div>

      {/* Chart card */}
      <div style={styles.chartCard}>
        <div style={styles.chartHeader}>
          <span
            style={{
              display: 'inline-block',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#8B5CF6',
            }}
          />
          Evaluation Scores Over Time
        </div>
        <EChartWrapper option={chartOption} loading={isLoading} height={340} />
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    fontFamily: "'Outfit', sans-serif",
    color: '#F0F4F8',
  },
  backButton: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    background: 'none',
    border: 'none',
    color: '#06B6D4',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    padding: '4px 0',
    fontFamily: 'inherit',
    alignSelf: 'flex-start',
  },
  summaryBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: '12px',
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '14px 16px',
  },
  summaryLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  agentName: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#F8FAFC',
  },
  badge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: '9999px',
    border: '1px solid',
    flexShrink: 0,
  },
  summaryRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    flexWrap: 'wrap',
  },
  summaryText: {
    fontSize: '13px',
    color: '#94A3B8',
  },
  editButton: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    background: 'transparent',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#CBD5E1',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    padding: '6px 12px',
    fontFamily: 'inherit',
    transition: 'all 0.15s',
  },
  chartCard: {
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '16px',
  },
  chartHeader: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#78909C',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '12px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
}
