import React, { useMemo, useState } from 'react'
import { useSessionTrajectory, type TrajectoryEvent } from '../../hooks/useSessionTrajectory'
import {
  ChevronRight,
  ChevronDown,
  Cpu,
  Wrench,
  Bot,
  AlertCircle,
  Clock,
  Zap,
  MessageSquare,
} from 'lucide-react'

// ─── Tree node with children built from parentSpanId ────────────────────────

interface TrajectoryTreeNode extends TrajectoryEvent {
  children: TrajectoryTreeNode[]
  depth: number
}

function buildTree(events: TrajectoryEvent[]): TrajectoryTreeNode[] {
  const nodeMap = new Map<string, TrajectoryTreeNode>()
  const roots: TrajectoryTreeNode[] = []

  // Create tree nodes
  for (const evt of events) {
    nodeMap.set(evt.spanId, { ...evt, children: [], depth: 0 })
  }

  // Build parent-child relationships
  for (const evt of events) {
    const node = nodeMap.get(evt.spanId)!
    if (evt.parentSpanId && nodeMap.has(evt.parentSpanId)) {
      const parent = nodeMap.get(evt.parentSpanId)!
      node.depth = parent.depth + 1
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  }

  // Propagate depths
  function setDepths(node: TrajectoryTreeNode, depth: number) {
    node.depth = depth
    for (const child of node.children) {
      setDepths(child, depth + 1)
    }
  }
  roots.forEach(r => setDepths(r, 0))

  return roots
}

function flattenTree(roots: TrajectoryTreeNode[], expanded: Set<string>): TrajectoryTreeNode[] {
  const result: TrajectoryTreeNode[] = []
  function walk(node: TrajectoryTreeNode) {
    result.push(node)
    if (expanded.has(node.spanId) || node.children.length === 0) {
      for (const child of node.children) {
        walk(child)
      }
    }
  }
  // If no parent-child relationships exist (flat data), just return all
  const hasTree = roots.some(r => r.children.length > 0)
  if (!hasTree) {
    // Flat mode: show all events expanded
    for (const r of roots) {
      result.push(r)
    }
    return result
  }
  for (const root of roots) {
    walk(root)
  }
  return result
}

// ─── Styles ─────────────────────────────────────────────────────────────────

const s = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
    overflow: 'hidden',
    background: '#0F172A',
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
    background: 'rgba(15, 23, 42, 0.6)',
  },
  headerStats: {
    display: 'flex',
    gap: '16px',
    alignItems: 'center',
  },
  statChip: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    color: '#94A3B8',
    background: 'rgba(30, 41, 59, 0.6)',
    padding: '4px 8px',
    borderRadius: '6px',
    border: '1px solid rgba(51, 65, 85, 0.5)',
  },
  scrollArea: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '0',
  },
  // Waterfall row
  row: {
    display: 'flex',
    alignItems: 'stretch',
    borderBottom: '1px solid rgba(51, 65, 85, 0.3)',
    cursor: 'pointer',
    transition: 'background 0.15s',
    minHeight: '36px',
  },
  rowHover: {
    background: 'rgba(56, 189, 248, 0.04)',
  },
  // Left tree + label column
  labelCol: {
    display: 'flex',
    alignItems: 'center',
    minWidth: '340px',
    maxWidth: '400px',
    padding: '6px 8px 6px 0',
    flexShrink: 0,
    borderRight: '1px solid rgba(51, 65, 85, 0.3)',
  },
  // Right waterfall bar area
  waterfallCol: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    padding: '4px 12px',
    position: 'relative' as const,
    minWidth: 0,
  },
  // Expand/collapse chevron
  chevron: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '16px',
    height: '16px',
    flexShrink: 0,
    color: '#64748B',
  },
  nodeIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '20px',
    height: '20px',
    borderRadius: '4px',
    flexShrink: 0,
    marginRight: '6px',
  },
  nodeLabel: {
    fontSize: '12px',
    fontWeight: 500,
    color: '#E2E8F0',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
    flex: 1,
  },
  // Waterfall bar
  waterfallBar: {
    height: '16px',
    borderRadius: '3px',
    position: 'relative' as const,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    paddingRight: '6px',
    fontSize: '10px',
    fontWeight: 600,
    color: 'rgba(255,255,255,0.9)',
    minWidth: '4px',
  },
  // Meta info on the right
  metaCol: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 12px',
    flexShrink: 0,
    minWidth: '200px',
    justifyContent: 'flex-end',
    borderLeft: '1px solid rgba(51, 65, 85, 0.3)',
    fontSize: '11px',
    color: '#94A3B8',
  },
  // Detail panel (expanded)
  detailPanel: {
    background: 'rgba(2, 6, 23, 0.6)',
    borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
    padding: '12px 16px 12px 56px',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '10px',
  },
  detailSection: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
  },
  detailHeading: {
    fontSize: '10px',
    fontWeight: 700,
    color: '#94A3B8',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
  },
  codeBlock: {
    background: '#020617',
    padding: '8px 10px',
    borderRadius: '6px',
    border: '1px solid rgba(255,255,255,0.06)',
    color: '#cbd5e1',
    whiteSpace: 'pre-wrap' as const,
    overflowX: 'auto' as const,
    fontSize: '11px',
    maxHeight: '200px',
    overflowY: 'auto' as const,
    lineHeight: '1.5',
  },
  evalChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '2px 8px',
    borderRadius: '10px',
    fontSize: '10px',
    fontWeight: 600,
  },
  tokenBar: {
    display: 'flex',
    height: '6px',
    borderRadius: '3px',
    overflow: 'hidden',
    background: 'rgba(255,255,255,0.05)',
    maxWidth: '200px',
  },
  logRow: {
    display: 'flex',
    gap: '8px',
    padding: '2px 0',
    borderBottom: '1px solid rgba(255,255,255,0.02)',
    fontSize: '10px',
  },
  spinner: {
    display: 'inline-block',
    width: '24px',
    height: '24px',
    border: '3px solid rgba(255,255,255,0.1)',
    borderRadius: '50%',
    borderTopColor: '#38BDF8',
    animation: 'spin 1s ease-in-out infinite',
  },
  statusBadge: {
    fontSize: '10px',
    fontWeight: 600,
    padding: '1px 6px',
    borderRadius: '4px',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '3px',
  },
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function getNodeTypeConfig(type: string): { color: string; bg: string; icon: React.ReactNode } {
  switch (type) {
    case 'LLM':
      return {
        color: '#A78BFA',
        bg: 'rgba(167, 139, 250, 0.15)',
        icon: <Cpu size={12} color="#A78BFA" />,
      }
    case 'Tool':
      return {
        color: '#34D399',
        bg: 'rgba(52, 211, 153, 0.15)',
        icon: <Wrench size={12} color="#34D399" />,
      }
    case 'Agent':
      return {
        color: '#38BDF8',
        bg: 'rgba(56, 189, 248, 0.15)',
        icon: <Bot size={12} color="#38BDF8" />,
      }
    default:
      return {
        color: '#94A3B8',
        bg: 'rgba(148, 163, 184, 0.15)',
        icon: <MessageSquare size={12} color="#94A3B8" />,
      }
  }
}

function formatDuration(ms: number): string {
  if (ms < 1) return '<1ms'
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

function formatTokens(count: number): string {
  if (count < 1000) return `${count}`
  if (count < 1000000) return `${(count / 1000).toFixed(1)}k`
  return `${(count / 1000000).toFixed(2)}M`
}

function formatJsonStr(jsonStr: string): string {
  try {
    const obj = JSON.parse(jsonStr)
    return JSON.stringify(obj, null, 2)
  } catch {
    return jsonStr
  }
}

function evalScoreColor(score: number): string {
  if (score >= 0.8) return '#10B981'
  if (score >= 0.5) return '#F59E0B'
  return '#EF4444'
}

function evalScoreBg(score: number): string {
  if (score >= 0.8) return 'rgba(16, 185, 129, 0.12)'
  if (score >= 0.5) return 'rgba(245, 158, 11, 0.12)'
  return 'rgba(239, 68, 68, 0.12)'
}

// ─── Component ──────────────────────────────────────────────────────────────

interface Props {
  sessionId: string | null
  activeTab: string
  viewMode: string
}

export const SessionLogsView: React.FC<Props> = ({ sessionId, activeTab, viewMode }) => {
  const { data, loading, error } = useSessionTrajectory(sessionId, activeTab, viewMode)
  const [expandedSpans, setExpandedSpans] = useState<Set<string>>(new Set())
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null)
  const [hoveredRow, setHoveredRow] = useState<string | null>(null)

  // Build tree from trajectory
  const tree = useMemo(() => {
    if (!data?.trajectory) return []
    return buildTree(data.trajectory)
  }, [data?.trajectory])

  // Flatten for display
  const flatNodes = useMemo(() => {
    // Start with all nodes expanded
    const allIds = new Set<string>()
    function collect(nodes: TrajectoryTreeNode[]) {
      for (const n of nodes) {
        if (n.children.length > 0) allIds.add(n.spanId)
        collect(n.children)
      }
    }
    collect(tree)
    return flattenTree(tree, expandedSpans.size > 0 ? expandedSpans : allIds)
  }, [tree, expandedSpans])

  // Compute waterfall metrics
  const { minTime, maxTime, totalDuration } = useMemo(() => {
    if (!data?.trajectory?.length) return { minTime: 0, maxTime: 0, totalDuration: 1 }
    let min = Infinity
    let max = -Infinity
    for (const evt of data.trajectory) {
      if (evt.startTime) {
        const t = new Date(evt.startTime).getTime()
        if (t < min) min = t
        const end = t + (evt.durationMs || 0)
        if (end > max) max = end
      }
    }
    return { minTime: min, maxTime: max, totalDuration: Math.max(max - min, 1) }
  }, [data?.trajectory])

  // Summary stats
  const stats = useMemo(() => {
    if (!data?.trajectory) return { llmCalls: 0, toolCalls: 0, totalTokens: 0, errors: 0, totalDuration: 0 }
    let llmCalls = 0, toolCalls = 0, totalTokens = 0, errors = 0
    for (const evt of data.trajectory) {
      if (evt.nodeType === 'LLM') llmCalls++
      if (evt.nodeType === 'Tool') toolCalls++
      totalTokens += evt.totalTokens || 0
      if (String(evt.statusCode) === '2' || String(evt.statusCode) === 'ERROR') errors++
    }
    return { llmCalls, toolCalls, totalTokens, errors, totalDuration: maxTime - minTime }
  }, [data?.trajectory, minTime, maxTime])

  const toggleExpand = (spanId: string) => {
    setExpandedSpans(prev => {
      const next = new Set(prev)
      if (next.has(spanId)) next.delete(spanId)
      else next.add(spanId)
      return next
    })
  }

  const toggleDetail = (spanId: string) => {
    setSelectedSpanId(prev => prev === spanId ? null : spanId)
  }

  if (!sessionId) {
    return <div style={{ padding: 24, color: '#94a3b8' }}>Select a session to view its execution trace.</div>
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '100px 0' }}>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <div style={s.spinner} />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24, color: '#EF4444', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', margin: 16 }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Error loading trace</h3>
        <p style={{ margin: 0 }}>{error.message || 'An unknown error occurred'}</p>
      </div>
    )
  }

  if (!data?.trajectory?.length) {
    return <div style={{ padding: 24, color: '#94a3b8' }}>No trace data found for this session.</div>
  }

  return (
    <div style={s.container}>
      {/* Summary header */}
      <div style={s.header}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#F0F4F8' }}>
          Session Trace
          <span style={{ color: '#64748B', fontWeight: 400, marginLeft: '8px' }}>
            {data.trajectory.length} spans
          </span>
        </div>
        <div style={s.headerStats}>
          <div style={s.statChip}>
            <Cpu size={11} color="#A78BFA" />
            <span style={{ color: '#A78BFA' }}>{stats.llmCalls}</span> LLM
          </div>
          <div style={s.statChip}>
            <Wrench size={11} color="#34D399" />
            <span style={{ color: '#34D399' }}>{stats.toolCalls}</span> Tools
          </div>
          <div style={s.statChip}>
            <Zap size={11} color="#FACC15" />
            {formatTokens(stats.totalTokens)} tokens
          </div>
          <div style={s.statChip}>
            <Clock size={11} />
            {formatDuration(stats.totalDuration)}
          </div>
          {stats.errors > 0 && (
            <div style={{ ...s.statChip, borderColor: 'rgba(248, 113, 113, 0.3)' }}>
              <AlertCircle size={11} color="#F87171" />
              <span style={{ color: '#F87171' }}>{stats.errors}</span> errors
            </div>
          )}
        </div>
      </div>

      {/* Waterfall trace list */}
      <div style={s.scrollArea}>
        {/* Column headers */}
        <div style={{
          ...s.row,
          background: 'rgba(15, 23, 42, 0.8)',
          cursor: 'default',
          position: 'sticky',
          top: 0,
          zIndex: 10,
          minHeight: '28px',
          borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
        }}>
          <div style={{ ...s.labelCol, padding: '4px 8px' }}>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Span
            </span>
          </div>
          <div style={{ ...s.waterfallCol, padding: '4px 12px' }}>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Waterfall
            </span>
          </div>
          <div style={{ ...s.metaCol, minWidth: '200px' }}>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Details
            </span>
          </div>
        </div>

        {flatNodes.map((node) => {
          const config = getNodeTypeConfig(node.nodeType)
          const hasChildren = node.children.length > 0
          const isExpanded = expandedSpans.has(node.spanId) || expandedSpans.size === 0
          const isSelected = selectedSpanId === node.spanId
          const isHovered = hoveredRow === node.spanId
          const isError = String(node.statusCode) === '2' || String(node.statusCode) === 'ERROR'

          // Waterfall bar position
          const startMs = node.startTime ? new Date(node.startTime).getTime() - minTime : 0
          const barLeft = totalDuration > 0 ? (startMs / totalDuration) * 100 : 0
          const barWidth = totalDuration > 0 ? Math.max(((node.durationMs || 0) / totalDuration) * 100, 0.5) : 1

          return (
            <React.Fragment key={node.spanId}>
              <div
                style={{
                  ...s.row,
                  ...(isHovered ? s.rowHover : {}),
                  ...(isSelected ? { background: 'rgba(6, 182, 212, 0.08)' } : {}),
                  ...(isError ? { borderLeft: '2px solid #F87171' } : {}),
                }}
                onMouseEnter={() => setHoveredRow(node.spanId)}
                onMouseLeave={() => setHoveredRow(null)}
                onClick={() => toggleDetail(node.spanId)}
              >
                {/* Label column with tree indentation */}
                <div style={s.labelCol}>
                  <div style={{ width: `${node.depth * 16}px`, flexShrink: 0 }} />

                  {/* Expand/collapse */}
                  {hasChildren ? (
                    <div
                      style={s.chevron}
                      onClick={(e) => { e.stopPropagation(); toggleExpand(node.spanId) }}
                    >
                      {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </div>
                  ) : (
                    <div style={{ width: '16px', flexShrink: 0 }} />
                  )}

                  {/* Node type icon */}
                  <div style={{ ...s.nodeIcon, background: config.bg }}>
                    {config.icon}
                  </div>

                  {/* Label */}
                  <span style={s.nodeLabel} title={node.nodeLabel}>
                    {node.nodeLabel || 'Unknown'}
                  </span>

                  {/* Model badge for LLM nodes */}
                  {node.model && (
                    <span style={{
                      fontSize: '9px',
                      color: '#A78BFA',
                      background: 'rgba(167, 139, 250, 0.1)',
                      border: '1px solid rgba(167, 139, 250, 0.2)',
                      borderRadius: '4px',
                      padding: '0 4px',
                      marginLeft: '4px',
                      flexShrink: 0,
                      whiteSpace: 'nowrap',
                    }}>
                      {node.model.replace('models/', '')}
                    </span>
                  )}
                </div>

                {/* Waterfall bar */}
                <div style={s.waterfallCol}>
                  <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center' }}>
                    <div
                      style={{
                        ...s.waterfallBar,
                        background: isError
                          ? 'linear-gradient(90deg, rgba(248, 113, 113, 0.6), rgba(248, 113, 113, 0.3))'
                          : `linear-gradient(90deg, ${config.color}99, ${config.color}44)`,
                        left: `${barLeft}%`,
                        width: `${barWidth}%`,
                        position: 'absolute',
                      }}
                    >
                      {node.durationMs > 0 && barWidth > 5 && (
                        <span style={{ fontSize: '9px' }}>{formatDuration(node.durationMs)}</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Meta details column */}
                <div style={s.metaCol}>
                  {node.durationMs > 0 && (
                    <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      {formatDuration(node.durationMs)}
                    </span>
                  )}
                  {node.totalTokens > 0 && (
                    <span style={{ color: '#FACC15' }}>
                      {formatTokens(node.totalTokens)}
                    </span>
                  )}
                  {isError && (
                    <span style={{
                      ...s.statusBadge,
                      color: '#F87171',
                      background: 'rgba(248, 113, 113, 0.1)',
                      border: '1px solid rgba(248, 113, 113, 0.2)',
                    }}>
                      <AlertCircle size={9} /> ERR
                    </span>
                  )}
                  {node.evaluations && node.evaluations.length > 0 && (
                    <span style={{
                      ...s.statusBadge,
                      color: '#A78BFA',
                      background: 'rgba(167, 139, 250, 0.1)',
                      border: '1px solid rgba(167, 139, 250, 0.2)',
                    }}>
                      Eval
                    </span>
                  )}
                </div>
              </div>

              {/* Expanded detail panel */}
              {isSelected && (
                <div style={s.detailPanel}>
                  {/* Status row */}
                  <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{
                      ...s.statusBadge,
                      fontSize: '11px',
                      color: config.color,
                      background: config.bg,
                      border: `1px solid ${config.color}33`,
                    }}>
                      {node.nodeType}
                    </span>
                    {node.model && (
                      <span style={{ fontSize: '11px', color: '#94A3B8' }}>
                        Model: <span style={{ color: '#A78BFA' }}>{node.model}</span>
                      </span>
                    )}
                    {node.startTime && (
                      <span style={{ fontSize: '11px', color: '#64748B' }}>
                        {new Date(node.startTime).toLocaleTimeString()}
                      </span>
                    )}
                    {node.durationMs > 0 && (
                      <span style={{ fontSize: '11px', color: '#94A3B8' }}>
                        Duration: <span style={{ color: '#F0F4F8' }}>{formatDuration(node.durationMs)}</span>
                      </span>
                    )}
                    {node.statusMessage && (
                      <span style={{ fontSize: '11px', color: isError ? '#F87171' : '#94A3B8' }}>
                        {node.statusMessage}
                      </span>
                    )}
                  </div>

                  {/* Token breakdown for LLM spans */}
                  {node.totalTokens > 0 && (
                    <div style={s.detailSection}>
                      <div style={s.detailHeading}>Token Usage</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={s.tokenBar}>
                          <div style={{
                            width: `${node.totalTokens > 0 ? (node.inputTokens / node.totalTokens) * 100 : 50}%`,
                            background: '#818CF8',
                            borderRadius: '3px 0 0 3px',
                          }} />
                          <div style={{
                            flex: 1,
                            background: '#34D399',
                            borderRadius: '0 3px 3px 0',
                          }} />
                        </div>
                        <span style={{ fontSize: '11px', color: '#818CF8' }}>
                          {formatTokens(node.inputTokens)} in
                        </span>
                        <span style={{ fontSize: '11px', color: '#34D399' }}>
                          {formatTokens(node.outputTokens)} out
                        </span>
                        <span style={{ fontSize: '11px', color: '#64748B' }}>
                          ({formatTokens(node.totalTokens)} total)
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Prompt/Input */}
                  {node.prompt && (
                    <div style={s.detailSection}>
                      <div style={s.detailHeading}>Prompt / Input</div>
                      <div style={s.codeBlock}>{formatJsonStr(node.prompt)}</div>
                    </div>
                  )}

                  {/* Tool Input */}
                  {node.toolInput && (
                    <div style={s.detailSection}>
                      <div style={s.detailHeading}>Tool Input (Arguments)</div>
                      <div style={s.codeBlock}>{formatJsonStr(node.toolInput)}</div>
                    </div>
                  )}

                  {/* Completion/Output */}
                  {node.completion && (
                    <div style={s.detailSection}>
                      <div style={s.detailHeading}>Completion / Response</div>
                      <div style={s.codeBlock}>{formatJsonStr(node.completion)}</div>
                    </div>
                  )}

                  {/* Tool Output */}
                  {node.toolOutput && (
                    <div style={s.detailSection}>
                      <div style={s.detailHeading}>Tool Output (Result)</div>
                      <div style={s.codeBlock}>{formatJsonStr(node.toolOutput)}</div>
                    </div>
                  )}

                  {/* Evaluations */}
                  {node.evaluations && node.evaluations.length > 0 && (
                    <div style={s.detailSection}>
                      <div style={s.detailHeading}>AI Evaluations</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {node.evaluations.map((ev, i) => (
                          <span
                            key={i}
                            title={ev.explanation}
                            style={{
                              ...s.evalChip,
                              color: evalScoreColor(ev.score),
                              background: evalScoreBg(ev.score),
                              border: `1px solid ${evalScoreColor(ev.score)}33`,
                            }}
                          >
                            {ev.metricName}: {ev.score.toFixed(2)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Correlated Logs */}
                  {node.logs && node.logs.length > 0 && (
                    <div style={s.detailSection}>
                      <div style={s.detailHeading}>Correlated Logs ({node.logs.length})</div>
                      <div style={{ ...s.codeBlock, background: 'rgba(0,0,0,0.3)', padding: '4px 8px' }}>
                        {node.logs.map((log, i) => {
                          const ld = log.timestamp ? new Date(log.timestamp) : null
                          const ltimeStr = ld
                            ? `${ld.getHours().toString().padStart(2, '0')}:${ld.getMinutes().toString().padStart(2, '0')}:${ld.getSeconds().toString().padStart(2, '0')}`
                            : '-'
                          const sev = log.severity || 'INFO'
                          let sevColor = '#38BDF8'
                          if (sev === 'WARNING') sevColor = '#FACC15'
                          if (sev === 'ERROR') sevColor = '#F87171'

                          let payloadStr = ''
                          if (typeof log.payload === 'string') payloadStr = log.payload
                          else payloadStr = JSON.stringify(log.payload, null, 2)

                          return (
                            <div key={i} style={s.logRow}>
                              <div style={{ color: '#64748B', whiteSpace: 'nowrap', minWidth: '60px' }}>{ltimeStr}</div>
                              <div style={{ fontWeight: 600, width: '50px', color: sevColor }}>{sev}</div>
                              <div style={{ color: '#cbd5e1', wordBreak: 'break-word' }}>{payloadStr}</div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}
