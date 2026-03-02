import type { MetricSeries } from '../../types/sre'
import { colors, typography } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'
import EChartWrapper from '../charts/EChartWrapper'
import type { EChartsOption } from 'echarts'

export default function MetricChart({ data }: { data: MetricSeries }) {
  const anomalyPoints = data.points
    .filter((p) => p.isAnomaly)
    .map((p) => ({
      coord: [p.timestamp, p.value],
      value: p.value,
    }))

  const option: EChartsOption = {
    title: {
      text: data.metricName,
      subtext: data.unit ? `Unit: ${data.unit}` : undefined,
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const list = Array.isArray(params) ? params : [params]
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const p = list[0] as any
        if (!p) return ''
        const ts = new Date(p.value[0]).toLocaleString()
        const val = typeof p.value[1] === 'number' ? p.value[1].toFixed(2) : p.value[1]
        return `<div style="font-family:${typography.monoFamily};font-size:12px">
          <div style="color:${colors.textMuted}">${ts}</div>
          <div style="color:${colors.textPrimary};font-weight:600">${val}${data.unit ? ' ' + data.unit : ''}</div>
        </div>`
      },
    },
    xAxis: {
      type: 'time',
    },
    yAxis: {
      type: 'value',
      name: data.unit ?? '',
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: colors.cyan },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: `${colors.cyan}30` },
              { offset: 1, color: `${colors.cyan}05` },
            ],
          } as unknown as string,
        },
        data: data.points.map((p) => [p.timestamp, p.value]),
        markPoint: anomalyPoints.length > 0
          ? {
              symbol: 'circle',
              symbolSize: 10,
              itemStyle: { color: colors.error },
              label: { show: false },
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              data: anomalyPoints as any,
            }
          : undefined,
      },
    ],
  }

  return (
    <div style={glassCard()}>
      <EChartWrapper option={option} height={280} />
    </div>
  )
}
