import { ResponsiveSankey } from '@nivo/sankey'
import type { SankeyResponse } from '../types'

interface TrajectorySankeyProps {
  data: SankeyResponse
}

export default function TrajectorySankey({ data }: TrajectorySankeyProps) {
  return (
    <div style={{ height: '600px', background: '#0d1117', borderRadius: '8px' }}>
      <ResponsiveSankey
        data={data}
        margin={{ top: 20, right: 160, bottom: 20, left: 160 }}
        align="justify"
        colors={(node) => {
          const matched = data.nodes.find((n) => n.id === node.id)
          return matched?.nodeColor ?? '#8b949e'
        }}
        nodeOpacity={0.85}
        nodeHoverOpacity={1}
        nodeThickness={18}
        nodeSpacing={24}
        nodeBorderWidth={1}
        nodeBorderColor={{ from: 'color', modifiers: [['darker', 0.4]] }}
        nodeBorderRadius={3}
        linkOpacity={0.4}
        linkHoverOpacity={0.6}
        linkContract={3}
        enableLinkGradient={true}
        labelPosition="outside"
        labelOrientation="horizontal"
        labelPadding={16}
        labelTextColor="#c9d1d9"
        theme={{
          background: '#0d1117',
          text: {
            fontSize: 12,
            fill: '#c9d1d9',
          },
          tooltip: {
            container: {
              background: '#161b22',
              color: '#c9d1d9',
              fontSize: '13px',
              borderRadius: '6px',
              border: '1px solid #30363d',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)',
            },
          },
        }}
      />
    </div>
  )
}
