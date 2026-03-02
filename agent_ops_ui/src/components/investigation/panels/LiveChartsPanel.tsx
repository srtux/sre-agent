/**
 * Live charts/analytics panel — renders VegaChartData items.
 * Shows raw JSON spec for now (Vega rendering requires additional library).
 */
import { useMemo } from 'react'
import { useDashboardStore } from '../../../stores/dashboardStore'
import DashboardCardWrapper from '../../common/DashboardCardWrapper'
import JsonPayloadViewer from '../../common/JsonPayloadViewer'
import { colors, typography, spacing } from '../../../theme/tokens'

const styles: Record<string, React.CSSProperties> = {
  placeholder: {
    fontSize: typography.sizes.sm,
    color: colors.textMuted,
    fontStyle: 'italic',
    marginBottom: spacing.sm,
  },
}

function ChartCard({ item }: { item: ReturnType<ReturnType<typeof useDashboardStore.getState>['itemsOfType']>[number] }) {
  const removeItem = useDashboardStore((s) => s.removeItem)
  const chart = item.vegaChart
  if (!chart) return null

  return (
    <DashboardCardWrapper
      title="Vega Chart"
      subtitle={item.toolName}
      timestamp={item.timestamp}
      onRemove={() => removeItem(item.id)}
    >
      <div style={styles.placeholder}>
        Vega rendering not yet available — showing raw spec
      </div>
      <JsonPayloadViewer data={chart.spec} maxHeight={400} />
      {chart.data && (
        <>
          <div style={{ ...styles.placeholder, marginTop: spacing.md }}>
            Data ({Array.isArray(chart.data) ? chart.data.length : 0} rows)
          </div>
          <JsonPayloadViewer data={chart.data} maxHeight={300} />
        </>
      )}
    </DashboardCardWrapper>
  )
}

export default function LiveChartsPanel() {
  const allItems = useDashboardStore((s) => s.items)
  const items = useMemo(() => allItems.filter((i) => i.type === 'analytics'), [allItems])

  return (
    <div>
      {items.map((item) => (
        <ChartCard key={item.id} item={item} />
      ))}
    </div>
  )
}
