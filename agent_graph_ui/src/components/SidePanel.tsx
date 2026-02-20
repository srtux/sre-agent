import { useState, useEffect } from 'react'
import axios from 'axios'
import type { SelectedElement, NodeDetail, EdgeDetail } from '../types'

interface SidePanelProps {
  selected: SelectedElement | null
  projectId: string
  hours: number
  onClose: () => void
}

/** Format a number into a compact human-readable string (e.g. 12500 -> "12.5K"). */
function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

/** Format a dollar amount (e.g. 0.0045 -> "$0.0045"). */
function formatCost(n: number): string {
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.01) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

/** Format milliseconds (e.g. 1200 -> "1.2s", 120 -> "120ms"). */
function formatLatency(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.round(ms)}ms`
}

/** Return a color for the given error rate percentage. */
function errorRateColor(rate: number): string {
  if (rate > 5) return '#f85149'
  if (rate > 1) return '#d29922'
  return '#3fb950'
}

/** Map node types to simple icons. */
function nodeTypeIcon(nodeType: string): string {
  const t = nodeType.toLowerCase()
  if (t.includes('agent') || t.includes('orchestrator')) return '\u2B22' // hexagon
  if (t.includes('tool')) return '\u2699' // gear
  if (t.includes('model') || t.includes('llm')) return '\u25C6' // diamond
  return '\u25CF' // circle
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    width: '360px',
    background: '#161b22',
    borderLeft: '1px solid #21262d',
    zIndex: 50,
    display: 'flex',
    flexDirection: 'column',
    transition: 'transform 0.25s ease-in-out',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px',
    borderBottom: '1px solid #21262d',
  },
  headerTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#e6edf3',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    marginRight: '8px',
  },
  closeButton: {
    background: 'transparent',
    border: 'none',
    color: '#8b949e',
    fontSize: '18px',
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: '4px',
    lineHeight: 1,
    flexShrink: 0,
  },
  body: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
  },
  section: {
    marginBottom: '20px',
  },
  sectionTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#8b949e',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    marginBottom: '10px',
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 0',
    fontSize: '13px',
  },
  rowLabel: {
    color: '#8b949e',
  },
  rowValue: {
    color: '#c9d1d9',
    fontWeight: 500,
    fontVariantNumeric: 'tabular-nums',
  },
  badge: {
    padding: '2px 8px',
    borderRadius: '10px',
    fontSize: '12px',
    fontWeight: 600,
  },
  latencyBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 0',
    fontSize: '13px',
  },
  latencyLabel: {
    color: '#8b949e',
    width: '32px',
    flexShrink: 0,
  },
  latencyTrack: {
    flex: 1,
    height: '6px',
    background: '#21262d',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  latencyFill: {
    height: '100%',
    borderRadius: '3px',
  },
  latencyValue: {
    color: '#c9d1d9',
    fontSize: '12px',
    fontVariantNumeric: 'tabular-nums',
    width: '56px',
    textAlign: 'right' as const,
    flexShrink: 0,
  },
  errorItem: {
    padding: '8px 10px',
    background: '#1c1a1a',
    border: '1px solid #30363d',
    borderRadius: '6px',
    marginBottom: '6px',
    fontSize: '12px',
  },
  errorMessage: {
    color: '#f85149',
    wordBreak: 'break-word' as const,
    marginBottom: '2px',
  },
  errorCount: {
    color: '#8b949e',
    fontSize: '11px',
  },
  spinner: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    color: '#8b949e',
    fontSize: '14px',
  },
  errorBox: {
    padding: '12px',
    background: '#3d1a1a',
    border: '1px solid #f85149',
    borderRadius: '6px',
    color: '#f85149',
    fontSize: '13px',
  },
}

export default function SidePanel({
  selected,
  projectId,
  hours,
  onClose,
}: SidePanelProps) {
  const [nodeDetail, setNodeDetail] = useState<NodeDetail | null>(null)
  const [edgeDetail, setEdgeDetail] = useState<EdgeDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selected) {
      setNodeDetail(null)
      setEdgeDetail(null)
      setError(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)
    setNodeDetail(null)
    setEdgeDetail(null)

    const params = { project_id: projectId, hours }

    const fetchData = async () => {
      try {
        if (selected.kind === 'node') {
          const encodedId = encodeURIComponent(selected.id)
          const res = await axios.get<NodeDetail>(
            `/api/v1/graph/node/${encodedId}`,
            { params },
          )
          if (!cancelled) setNodeDetail(res.data)
        } else {
          const encodedSource = encodeURIComponent(selected.sourceId)
          const encodedTarget = encodeURIComponent(selected.targetId)
          const res = await axios.get<EdgeDetail>(
            `/api/v1/graph/edge/${encodedSource}/${encodedTarget}`,
            { params },
          )
          if (!cancelled) setEdgeDetail(res.data)
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : 'Failed to load details',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [selected, projectId, hours])

  const isOpen = selected !== null

  return (
    <div
      style={{
        ...styles.overlay,
        transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
        pointerEvents: isOpen ? 'auto' : 'none',
      }}
    >
      <div style={styles.header}>
        <span style={styles.headerTitle}>
          {selected?.kind === 'node' && nodeDetail && (
            <>
              <span style={{ marginRight: '6px' }}>
                {nodeTypeIcon(nodeDetail.nodeType)}
              </span>
              {nodeDetail.label}
            </>
          )}
          {selected?.kind === 'edge' && edgeDetail && (
            <>{edgeDetail.sourceId} &rarr; {edgeDetail.targetId}</>
          )}
          {loading && 'Loading...'}
          {error && 'Error'}
        </span>
        <button
          style={styles.closeButton}
          onClick={onClose}
          title="Close panel"
        >
          &times;
        </button>
      </div>

      <div style={styles.body}>
        {loading && <div style={styles.spinner}>Loading details...</div>}

        {error && <div style={styles.errorBox}>{error}</div>}

        {nodeDetail && !loading && !error && (
          <NodeDetailView detail={nodeDetail} />
        )}

        {edgeDetail && !loading && !error && (
          <EdgeDetailView detail={edgeDetail} />
        )}
      </div>
    </div>
  )
}

function NodeDetailView({ detail }: { detail: NodeDetail }) {
  const errColor = errorRateColor(detail.errorRate)
  const maxLatency = detail.latency.p99 || 1

  return (
    <>
      {/* Metrics */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Metrics</div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Total Invocations</span>
          <span style={styles.rowValue}>
            {detail.totalInvocations.toLocaleString()}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Error Rate</span>
          <span
            style={{
              ...styles.badge,
              color: '#fff',
              background: errColor,
            }}
          >
            {detail.errorRate.toFixed(1)}%
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Error Count</span>
          <span style={{ ...styles.rowValue, color: detail.errorCount > 0 ? '#f85149' : '#c9d1d9' }}>
            {detail.errorCount.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Tokens */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Tokens</div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Input Tokens</span>
          <span style={styles.rowValue}>
            {formatTokens(detail.inputTokens)}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Output Tokens</span>
          <span style={styles.rowValue}>
            {formatTokens(detail.outputTokens)}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Total</span>
          <span style={styles.rowValue}>
            {formatTokens(detail.inputTokens + detail.outputTokens)}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Estimated Cost</span>
          <span style={styles.rowValue}>
            {formatCost(detail.estimatedCost)}
          </span>
        </div>
      </div>

      {/* Latency */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Latency</div>
        {(['p50', 'p95', 'p99'] as const).map((pct) => {
          const value = detail.latency[pct]
          const widthPct = maxLatency > 0 ? (value / maxLatency) * 100 : 0
          const barColors: Record<string, string> = {
            p50: '#3fb950',
            p95: '#d29922',
            p99: '#f85149',
          }
          return (
            <div key={pct} style={styles.latencyBar}>
              <span style={styles.latencyLabel}>
                {pct.toUpperCase()}
              </span>
              <div style={styles.latencyTrack}>
                <div
                  style={{
                    ...styles.latencyFill,
                    width: `${Math.min(widthPct, 100)}%`,
                    background: barColors[pct],
                  }}
                />
              </div>
              <span style={styles.latencyValue}>
                {formatLatency(value)}
              </span>
            </div>
          )
        })}
      </div>

      {/* Top Errors */}
      {detail.topErrors.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Top Errors</div>
          {detail.topErrors.map((err, idx) => (
            <div key={idx} style={styles.errorItem}>
              <div style={styles.errorMessage}>{err.message}</div>
              <div style={styles.errorCount}>
                {err.count.toLocaleString()} occurrence{err.count !== 1 ? 's' : ''}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function EdgeDetailView({ detail }: { detail: EdgeDetail }) {
  const errColor = errorRateColor(detail.errorRate)

  return (
    <>
      {/* Call metrics */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Call Metrics</div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Call Count</span>
          <span style={styles.rowValue}>
            {detail.callCount.toLocaleString()}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Error Count</span>
          <span style={{ ...styles.rowValue, color: detail.errorCount > 0 ? '#f85149' : '#c9d1d9' }}>
            {detail.errorCount.toLocaleString()}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Error Rate</span>
          <span
            style={{
              ...styles.badge,
              color: '#fff',
              background: errColor,
            }}
          >
            {detail.errorRate.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Performance */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Performance</div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Avg Duration</span>
          <span style={styles.rowValue}>
            {formatLatency(detail.avgDurationMs)}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>P95 Duration</span>
          <span style={styles.rowValue}>
            {formatLatency(detail.p95DurationMs)}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>P99 Duration</span>
          <span style={styles.rowValue}>
            {formatLatency(detail.p99DurationMs)}
          </span>
        </div>
      </div>

      {/* Tokens */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Tokens</div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Total</span>
          <span style={styles.rowValue}>
            {formatTokens(detail.totalTokens)}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Input</span>
          <span style={styles.rowValue}>
            {formatTokens(detail.inputTokens)}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.rowLabel}>Output</span>
          <span style={styles.rowValue}>
            {formatTokens(detail.outputTokens)}
          </span>
        </div>
      </div>
    </>
  )
}
