import React, { useEffect } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { useDashboardMetrics } from '../../../hooks/useDashboardMetrics'

const PULSE_KEYFRAME_ID = '__kpi-pulse-keyframe'

const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: 12,
}

const cardStyle: React.CSSProperties = {
  background: '#1E293B',
  border: '1px solid #334155',
  borderRadius: 8,
  padding: '16px 20px',
}

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 500,
  color: '#78909C',
  textTransform: 'uppercase',
  letterSpacing: 0.5,
  margin: 0,
}

const valueStyle: React.CSSProperties = {
  fontSize: 28,
  fontWeight: 700,
  color: '#F0F4F8',
  margin: '4px 0',
}

const trendRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  fontSize: 12,
}

const errorStyle: React.CSSProperties = {
  background: 'rgba(255, 82, 82, 0.08)',
  border: '1px solid rgba(255, 82, 82, 0.3)',
  borderRadius: 6,
  color: '#FF5252',
  padding: '12px 16px',
  fontSize: 14,
}

const skeletonBar = (width: number | string, height: number): React.CSSProperties => ({
  background: '#334155',
  borderRadius: 4,
  width,
  height,
  animation: 'kpi-pulse 1.5s ease-in-out infinite',
})

interface KpiItem {
  label: string
  value: string
  trend: number
}

function TrendIndicator({ trend }: { trend: number }) {
  if (trend > 0) {
    return (
      <span style={{ ...trendRowStyle, color: '#10B981' }}>
        <TrendingUp size={14} />
        +{trend.toFixed(1)}%
      </span>
    )
  }
  if (trend < 0) {
    return (
      <span style={{ ...trendRowStyle, color: '#EF4444' }}>
        <TrendingDown size={14} />
        {trend.toFixed(1)}%
      </span>
    )
  }
  return (
    <span style={{ ...trendRowStyle, color: '#78909C' }}>
      0.0%
    </span>
  )
}

function SkeletonCards() {
  useEffect(() => {
    if (!document.getElementById(PULSE_KEYFRAME_ID)) {
      const style = document.createElement('style')
      style.id = PULSE_KEYFRAME_ID
      style.textContent = '@keyframes kpi-pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 0.8; } }'
      document.head.appendChild(style)
    }
  }, [])

  return (
    <div style={gridStyle}>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} style={cardStyle}>
          <div style={skeletonBar(80, 10)} />
          <div style={{ ...skeletonBar(120, 24), marginTop: 8 }} />
          <div style={{ ...skeletonBar(60, 12), marginTop: 8 }} />
        </div>
      ))}
    </div>
  )
}

export default function KpiGrid({ hours }: { hours: number }) {
  const { data, isLoading, isError } = useDashboardMetrics(hours)

  if (isLoading) {
    return <SkeletonCards />
  }

  if (isError) {
    return (
      <div style={errorStyle}>
        Failed to load KPI metrics.
      </div>
    )
  }

  const kpis: KpiItem[] = [
    {
      label: 'Total Sessions',
      value: data!.kpis.totalSessions.toLocaleString(),
      trend: data!.kpis.totalSessionsTrend,
    },
    {
      label: 'Avg Turns',
      value: data!.kpis.avgTurns.toFixed(1),
      trend: data!.kpis.avgTurnsTrend,
    },
    {
      label: 'Root Invocations',
      value: data!.kpis.rootInvocations.toLocaleString(),
      trend: data!.kpis.rootInvocationsTrend,
    },
    {
      label: 'Error Rate',
      value: (data!.kpis.errorRate * 100).toFixed(1) + '%',
      trend: data!.kpis.errorRateTrend,
    },
  ]

  return (
    <div style={gridStyle}>
      {kpis.map((kpi) => (
        <div key={kpi.label} style={cardStyle}>
          <div style={labelStyle}>{kpi.label}</div>
          <div style={valueStyle}>{kpi.value}</div>
          <TrendIndicator trend={kpi.trend} />
        </div>
      ))}
    </div>
  )
}
