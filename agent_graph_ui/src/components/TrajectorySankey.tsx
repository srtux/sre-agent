import { ResponsiveSankey } from '@nivo/sankey'
import type { SankeyResponse } from '../types'
import { removeCyclicLinks } from '../utils/sankeyUtils'

interface TrajectorySankeyProps {
  data: SankeyResponse
}

export default function TrajectorySankey({ data }: TrajectorySankeyProps) {
  // Build a Set of node IDs involved in detected loops
  const loopNodeIds = new Set<string>()
  const loopEdges = new Set<string>()
  if (data.loopTraces) {
    for (const lt of data.loopTraces) {
      for (const loop of lt.loops) {
        for (const nodeId of loop.cycle) {
          loopNodeIds.add(nodeId)
        }
        // Mark edges between consecutive cycle nodes
        for (let i = 0; i < loop.cycle.length; i++) {
          const src = loop.cycle[i]
          const tgt = loop.cycle[(i + 1) % loop.cycle.length]
          loopEdges.add(`${src}->${tgt}`)
        }
      }
    }
  }

  const hasLoops = loopNodeIds.size > 0
  const safeData = removeCyclicLinks(data)

  return (
    <div style={{ width: '100vw', height: '100vh', paddingBottom: '100px', background: '#0d1117', borderRadius: hasLoops ? '8px 8px 0 0' : '8px' }}>
      <ResponsiveSankey
        data={safeData}
        margin={{ top: 20, right: 160, bottom: 20, left: 160 }}
        align="justify"
        colors={(node) => {
          if (loopNodeIds.has(node.id)) return '#FF6D00' // bright orange for loop nodes
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
        nodeTooltip={(props) => {
          const nodeId = props.node.id
          const isLoop = loopNodeIds.has(String(nodeId))
          return (
            <div style={{
              background: '#161b22',
              color: '#c9d1d9',
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid #30363d',
              fontSize: '13px',
            }}>
              <div style={{ fontWeight: 600 }}>{String(nodeId)}</div>
              {isLoop && (
                <div style={{ color: '#FF6D00', marginTop: '4px', fontSize: '12px' }}>
                  {'\u26A0'} Pathological loop detected
                </div>
              )}
            </div>
          )
        }}
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
      {hasLoops && (
        <div style={{
          padding: '8px 16px',
          background: 'rgba(255, 109, 0, 0.1)',
          border: '1px solid #FF6D00',
          borderRadius: '0 0 8px 8px',
          borderTop: 'none',
          color: '#FF6D00',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>{'\u26A0'}</span>
          <span>
            {data.loopTraces!.length} trace{data.loopTraces!.length !== 1 ? 's' : ''} with pathological loops detected.
            Highlighted nodes are stuck in retry cycles.
          </span>
        </div>
      )}
    </div>
  )
}
