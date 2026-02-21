import { ResponsiveSankey } from '@nivo/sankey'
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch'
import type { SankeyResponse } from '../types'
import { removeCyclicLinks } from '../utils/sankeyUtils'
import { ZoomIn, ZoomOut, Maximize } from 'lucide-react'

const agentColors: Record<string, string> = {
  user: '#9CA3AF',             // Gray 400
  receptionist: '#8B5CF6',     // Violet 500
  triage: '#A78BFA',           // Violet 400
  log_analyzer: '#3B82F6',     // Blue 500
  metrics_analyzer: '#06B6D4', // Cyan 500
  researcher: '#F59E0B',       // Amber 500
  answer_drafter: '#10B981',   // Emerald 500
};

const getAgentColor = (node: { id: string }) => agentColors[node.id] || '#6366F1';

interface TrajectorySankeyProps {
  data: SankeyResponse
  onNodeClick?: (nodeId: string) => void
  onEdgeClick?: (sourceId: string, targetId: string) => void
}

export default function TrajectorySankey({ data, onNodeClick, onEdgeClick }: TrajectorySankeyProps) {
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

  // Dynamic dimensions based on node count to prevent squishing
  const numNodes = safeData.nodes.length
  const dynamicHeight = Math.max(800, numNodes * 60)
  const dynamicWidth = Math.max(1200, numNodes * 80)

  const controlButtonStyle = {
    background: 'transparent',
    border: 'none',
    color: '#94A3B8',
    cursor: 'pointer',
    padding: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '4px',
  }

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#0F172A', overflow: 'hidden' }}>
      <TransformWrapper
        initialScale={1}
        minScale={0.1}
        maxScale={4}
        centerOnInit={true}
        limitToBounds={false}
      >
        {({ zoomIn, zoomOut, resetTransform }) => (
          <>
            <TransformComponent wrapperStyle={{ width: '100%', height: '100%' }} contentStyle={{ width: dynamicWidth, height: dynamicHeight }}>
              <div style={{ width: dynamicWidth, height: dynamicHeight }}>
                <ResponsiveSankey
                  data={safeData}
                  margin={{ top: 40, right: 160, bottom: 40, left: 50 }}
                  align="justify"
                  colors={(node) => loopNodeIds.has(node.id) ? '#FF6D00' : getAgentColor(node)}
                  nodeOpacity={1}
                  nodeThickness={16}
                  nodeInnerPadding={3}
                  nodeSpacing={24}
                  nodeBorderWidth={0}
                  nodeBorderRadius={2}
                  linkOpacity={0.15}
                  linkHoverOthersOpacity={0.05}
                  linkContract={2}
                  linkBlendMode="screen"
                  enableLinkGradient={true}
                  labelPosition="outside"
                  labelOrientation="horizontal"
                  labelPadding={16}
                  labelTextColor="#E5E7EB"
                  nodeHoverOthersOpacity={0.2}
                  animate={true}
                  onClick={(datum) => {
                    if ('source' in datum && 'target' in datum) {
                      // It's a link
                      const sourceId = (datum.source as { id?: string }).id || datum.source
                      const targetId = (datum.target as { id?: string }).id || datum.target
                      onEdgeClick?.(String(sourceId), String(targetId))
                    } else {
                      // It's a node
                      onNodeClick?.(String(datum.id))
                    }
                  }}
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
          background: 'transparent',
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
            </TransformComponent>
            <div style={{
              position: 'absolute',
              top: 16,
              right: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              zIndex: 10,
              background: '#1E293B',
              border: '1px solid #334155',
              borderRadius: '6px',
              padding: '4px'
            }}>
              <button onClick={() => zoomIn(0.25)} style={controlButtonStyle as React.CSSProperties} title="Zoom In"><ZoomIn size={16} /></button>
              <button onClick={() => zoomOut(0.25)} style={controlButtonStyle as React.CSSProperties} title="Zoom Out"><ZoomOut size={16} /></button>
              <button onClick={() => resetTransform()} style={controlButtonStyle as React.CSSProperties} title="Reset View"><Maximize size={16} /></button>
            </div>
          </>
        )}
      </TransformWrapper>
      {hasLoops && (
        <div style={{
          position: 'absolute',
          bottom: 16,
          left: '50%',
          transform: 'translateX(-50%)',
          padding: '8px 16px',
          background: 'rgba(255, 109, 0, 0.1)',
          border: '1px solid #FF6D00',
          borderRadius: '8px',
          color: '#FF6D00',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          zIndex: 20,
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
