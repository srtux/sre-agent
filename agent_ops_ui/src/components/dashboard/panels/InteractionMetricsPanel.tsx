import { useMemo } from 'react'
import type { EChartsOption } from 'echarts'
import EChartWrapper from '../../charts/EChartWrapper'
import { useDashboardMetrics } from '../../../hooks/useDashboardMetrics'

function formatTimestamp(iso: string, hours: number): string {
  const date = new Date(iso)
  if (hours <= 24) {
    return date.toLocaleString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  }
  return date.toLocaleString('en-US', { month: 'short', day: '2-digit' })
}

export default function InteractionMetricsPanel({ hours }: { hours: number }) {
  const { data, isLoading } = useDashboardMetrics(hours)

  const latencyOption = useMemo((): EChartsOption => {
    if (!data?.latency) return { series: [] }
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: { top: 0, right: 0 },
      xAxis: {
        type: 'category',
        data: data.latency.map(p => formatTimestamp(p.timestamp, hours)),
        axisLabel: { rotate: 0 }
      },
      yAxis: { type: 'value', name: 'ms' },
      series: [
        {
          name: 'P50',
          type: 'line',
          smooth: true,
          data: data.latency.map(p => p.p50),
          itemStyle: { color: '#06B6D4' },
          lineStyle: { width: 2, color: '#06B6D4' }
        },
        {
          name: 'P95',
          type: 'line',
          smooth: true,
          data: data.latency.map(p => p.p95),
          itemStyle: { color: '#8B5CF6' },
          lineStyle: { width: 2, color: '#8B5CF6' }
        }
      ]
    }
  }, [data?.latency, hours])

  const qpsOption = useMemo((): EChartsOption => {
    if (!data?.qps) return { series: [] }
    return {
      tooltip: { trigger: 'axis' },
      grid: { right: 60 },
      xAxis: {
        type: 'category',
        data: data.qps.map(p => formatTimestamp(p.timestamp, hours))
      },
      yAxis: [
        { type: 'value', name: 'QPS' },
        {
          type: 'value',
          name: 'Error %',
          axisLabel: {
            formatter: (value: number) => `${(value * 100).toFixed(0)}%`
          }
        }
      ],
      series: [
        {
          name: 'QPS',
          type: 'bar',
          yAxisIndex: 0,
          data: data.qps.map(p => p.qps),
          itemStyle: { color: '#06B6D4' },
          barMaxWidth: 20
        },
        {
          name: 'Error Rate',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          data: data.qps.map(p => p.errorRate),
          itemStyle: { color: '#EF4444' },
          lineStyle: { width: 2, color: '#EF4444' }
        }
      ]
    }
  }, [data?.qps, hours])

  const tokenOption = useMemo((): EChartsOption => {
    if (!data?.tokens) return { series: [] }
    return {
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: data.tokens.map(p => formatTimestamp(p.timestamp, hours))
      },
      yAxis: { type: 'value', name: 'Tokens' },
      series: [
        {
          name: 'Input Tokens',
          type: 'line',
          stack: 'tokens',
          data: data.tokens.map(p => p.input),
          itemStyle: { color: '#06B6D4' },
          areaStyle: { opacity: 0.3 }
        },
        {
          name: 'Output Tokens',
          type: 'line',
          stack: 'tokens',
          data: data.tokens.map(p => p.output),
          itemStyle: { color: '#8B5CF6' },
          areaStyle: { opacity: 0.3 }
        }
      ]
    }
  }, [data?.tokens, hours])

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
      <div style={{ background: '#1E293B', border: '1px solid #334155', borderRadius: '8px', padding: '16px' }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#78909C', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px' }}>
          Latency Over Time
        </div>
        <EChartWrapper option={latencyOption} loading={isLoading} height={280} />
      </div>
      <div style={{ background: '#1E293B', border: '1px solid #334155', borderRadius: '8px', padding: '16px' }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#78909C', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px' }}>
          QPS & Error Rate
        </div>
        <EChartWrapper option={qpsOption} loading={isLoading} height={280} />
      </div>
      <div style={{ background: '#1E293B', border: '1px solid #334155', borderRadius: '8px', padding: '16px', gridColumn: '1 / -1' }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#78909C', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px' }}>
          Token Usage
        </div>
        <EChartWrapper option={tokenOption} loading={isLoading} height={280} />
      </div>
    </div>
  )
}
