import { useCallback, useEffect, useState, useRef } from 'react'
import {
  Edge,
  Node,
  Panel,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Play, Pause, StepForward, StepBack, SkipBack, SkipForward } from 'lucide-react'
import nodeTypes from './CustomNodes'
import TopologyGraph from '../TopologyGraph'

import { useAgentGraph } from '../../hooks/useAgentGraph'

interface Props {
  sessionId: string | null
  onNodeSelect: (nodeId: string | null) => void
}

export default function ContextGraphViewer({ sessionId, onNodeSelect }: Props) {
  const { nodes: initialNodes, edges: initialEdges } = useAgentGraph(sessionId)

  const [nodes, setNodes] = useState<Node[]>([])
  const [edges, setEdges] = useState<Edge[]>([])

  // Playback state
  const [playbackIndex, setPlaybackIndex] = useState<number>(0)
  const [isPlaying, setIsPlaying] = useState<boolean>(false)
  const playbackIntervalRef = useRef<number | null>(null)

  const maxIndex = initialNodes.length

  useEffect(() => {
    // Reset playback when session changes or new data arrives
    setPlaybackIndex(initialNodes.length)
    setIsPlaying(false)
  }, [initialNodes, initialEdges])

  useEffect(() => {
    // Filter nodes and edges based on playbackIndex
    const visibleNodes = initialNodes.slice(0, playbackIndex)
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id))
    const visibleEdges = initialEdges.filter(e => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target))

    setNodes(visibleNodes)
    setEdges(visibleEdges)
  }, [playbackIndex, initialNodes, initialEdges, setNodes, setEdges])

  useEffect(() => {
    if (isPlaying) {
      playbackIntervalRef.current = setInterval(() => {
        setPlaybackIndex(prev => {
          if (prev >= maxIndex) {
            setIsPlaying(false)
            return prev
          }
          return prev + 1
        })
      }, 1000) // 1 second per step
    } else {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current)
      }
    }

    return () => {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current)
      }
    }
  }, [isPlaying, maxIndex])

  const togglePlayback = useCallback(() => {
    if (playbackIndex >= maxIndex) {
      setPlaybackIndex(1) // Restart if at the end
    }
    setIsPlaying(prev => !prev)
  }, [playbackIndex, maxIndex])

  const stepForward = useCallback(() => {
    setIsPlaying(false)
    setPlaybackIndex(prev => Math.min(prev + 1, maxIndex))
  }, [maxIndex])

  const stepBack = useCallback(() => {
    setIsPlaying(false)
    setPlaybackIndex(prev => Math.max(prev - 1, 0))
  }, [])

  const skipToStart = useCallback(() => {
    setIsPlaying(false)
    setPlaybackIndex(0)
  }, [])

  const skipToEnd = useCallback(() => {
    setIsPlaying(false)
    setPlaybackIndex(maxIndex)
  }, [maxIndex])

  const onPaneClick = useCallback(() => {
    onNodeSelect(null)
  }, [onNodeSelect])

  if (!sessionId) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94A3B8', background: '#0F172A', borderRadius: '8px' }}>
        Select a session to view its context graph
      </div>
    )
  }

  const controlBtnStyle = {
    background: '#334155',
    border: 'none',
    color: '#F0F4F8',
    borderRadius: '4px',
    padding: '6px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.2s',
  }

  return (
    <div style={{ width: '100%', height: '100%', background: '#0F172A', borderRadius: '8px', overflow: 'hidden', position: 'relative' }}>
      <TopologyGraph
        nodes={nodes}
        edges={edges}
        customNodeTypes={nodeTypes}
        onNodeClick={onNodeSelect}
        onPaneClick={onPaneClick}
      >
        <Panel position="bottom-center" style={{ marginBottom: '16px' }}>
          <div style={{
            background: '#1E293B',
            padding: '8px 16px',
            borderRadius: '8px',
            border: '1px solid #334155',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
          }}>
            <button
              onClick={skipToStart}
              disabled={playbackIndex === 0}
              style={{ ...controlBtnStyle, opacity: playbackIndex === 0 ? 0.5 : 1 }}
              title="Skip to Start"
            >
              <SkipBack size={18} />
            </button>
            <button
              onClick={stepBack}
              disabled={playbackIndex === 0}
              style={{ ...controlBtnStyle, opacity: playbackIndex === 0 ? 0.5 : 1 }}
              title="Step Back"
            >
              <StepBack size={18} />
            </button>
            <button
              onClick={togglePlayback}
              style={{ ...controlBtnStyle, background: '#3B82F6', padding: '8px' }}
              title={isPlaying ? "Pause" : "Play"}
            >
              {isPlaying ? <Pause size={20} /> : <Play size={20} />}
            </button>
            <button
              onClick={stepForward}
              disabled={playbackIndex >= maxIndex}
              style={{ ...controlBtnStyle, opacity: playbackIndex >= maxIndex ? 0.5 : 1 }}
              title="Step Forward"
            >
              <StepForward size={18} />
            </button>
            <button
              onClick={skipToEnd}
              disabled={playbackIndex >= maxIndex}
              style={{ ...controlBtnStyle, opacity: playbackIndex >= maxIndex ? 0.5 : 1 }}
              title="Skip to End"
            >
              <SkipForward size={18} />
            </button>

            <div style={{
              width: '1px',
              height: '24px',
              background: '#334155',
              margin: '0 4px'
            }} />

            <span style={{
              color: '#94A3B8',
              fontSize: '12px',
              fontFamily: "'JetBrains Mono', monospace",
              minWidth: '60px',
              textAlign: 'center'
            }}>
              {playbackIndex} / {maxIndex}
            </span>
          </div>
        </Panel>
      </TopologyGraph>
    </div>
  )
}
