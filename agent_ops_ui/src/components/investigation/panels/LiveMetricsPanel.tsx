/**
 * Live metrics panel — responsive grid of metric cards and mini charts.
 * Renders MetricsDashboardData as status cards, MetricSeries as line charts.
 */
import { useMemo } from 'react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import EChartWrapper from '../../charts/EChartWrapper'
import { colors, typography, spacing } from '../../../theme/tokens'
import { glassCard } from '../../../theme/glassStyles'
import type { DashboardMetric, MetricSeries } from '../../../types/sre'
import type { EChartsOption } from 'echarts'

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: spacing.lg,
  },
  metricCard: {
    ...glassCard(),
    padding: spacing.lg,
  },
  metricHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  metricName: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    flexShrink: 0,
  },
  metricValue: {
    fontSize: typography.sizes.xxl,
    fontWeight: typography.weights.bold,
    color: colors.textPrimary,
  },
  metricUnit: {
    fontSize: typography.sizes.sm,
    color: colors.textMuted,
    marginLeft: 4,
  },
  delta: {
    fontSize: typography.sizes.xs,
    marginTop: 2,
  },
}

function statusDotColor(status: string): string {
  switch (status) {
    case 'critical': return colors.critical
    case 'warning': return colors.warning
    case 'normal': return colors.success
    default: return colors.textMuted
  }
}

function MetricStatusCard({ metric }: { metric: DashboardMetric }) {
  const delta = metric.previousValue != null
    ? metric.currentValue - metric.previousValue
    : null

  return (
    <div style={styles.metricCard}>
      <div style={styles.metricHeader}>
        <span style={styles.metricName}>{metric.name}</span>
        <span style={{ ...styles.statusDot, background: statusDotColor(metric.status) }} />
      </div>
      <div>
        <span style={styles.metricValue}>{metric.currentValue.toLocaleString()}</span>
        <span style={styles.metricUnit}>{metric.unit}</span>
      </div>
      {delta != null && (
        <div style={{
          ...styles.delta,
          color: delta > 0 ? colors.error : delta < 0 ? colors.success : colors.textMuted,
        }}>
          {delta > 0 ? '▲' : delta < 0 ? '▼' : '–'} {Math.abs(delta).toLocaleString()}
        </div>
      )}
    </div>
  )
}

function MiniLineChart({ series }: { series: MetricSeries }) {
  const option: EChartsOption = {
    grid: { left: 4, right: 4, top: 8, bottom: 4, containLabel: false },
    xAxis: {
      type: 'category',
      show: false,
      data: series.points.map((p) => p.timestamp),
    },
    yAxis: { type: 'value', show: false },
    series: [
      {
        type: 'line',
        data: series.points.map((p) => p.value),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.15 },
      },
    ],
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const p = Array.isArray(params) ? params[0] : params
        const data = (p as { value?: number; name?: string })
        return `${data.name}<br/>${data.value?.toLocaleString() ?? ''} ${series.unit ?? ''}`
      },
    },
  }

  return (
    <div style={styles.metricCard}>
      <div style={styles.metricName}>{series.metricName}</div>
      <EChartWrapper option={option} height={120} />
    </div>
  )
}

export default function LiveMetricsPanel() {
  const allItems = useDashboardStore((s) => s.items)
  const items = useMemo(() => allItems.filter((i) => i.type === 'metrics'), [allItems])
  // Collect all metric cards and series
  const elements: React.ReactNode[] = []

  for (const item of items) {
    if (item.metricsDashboard) {
      for (const metric of item.metricsDashboard.metrics) {
        elements.push(<MetricStatusCard key={`${item.id}-${metric.id}`} metric={metric} />)
      }
    }
    if (item.metricSeries) {
      elements.push(<MiniLineChart key={item.id} series={item.metricSeries} />)
    }
  }

  return (
    <div style={styles.grid}>
      {elements}
    </div>
  )
}
