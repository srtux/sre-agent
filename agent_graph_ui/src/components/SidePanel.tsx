import { useState, useEffect } from 'react'
import axios from 'axios'
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import json from 'react-syntax-highlighter/dist/esm/languages/hljs/json'
import sql from 'react-syntax-highlighter/dist/esm/languages/hljs/sql'
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs'
import type { SelectedElement, NodeDetail, EdgeDetail, PayloadEntry, ViewMode, TimeSeriesData } from '../types'
import Sparkline, { extractSparkSeries, sparkColor, sparkLabel } from './Sparkline'
import {
  User,
  Bot,
  Wrench,
  Sparkles,
  Activity,
  AlertCircle,
  FileDigit,
  Hash,
  Database,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Clock
} from 'lucide-react'

SyntaxHighlighter.registerLanguage('json', json)
SyntaxHighlighter.registerLanguage('sql', sql)

interface SidePanelProps {
  selected: SelectedElement | null
  projectId: string
  hours: number
  onClose: () => void
  viewMode?: ViewMode
  sparklineData?: TimeSeriesData | null
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
  if (rate > 5) return '#FF5252'
  if (rate > 1) return '#FBBF24'
  return '#34D399'
}

/** Map node types to React elements (Lucide icons). */
function NodeTypeIcon({ nodeType, size = 16, color = '#78909C' }: { nodeType: string, size?: number, color?: string }) {
  const t = nodeType.toLowerCase()
  if (t === 'user') return <User size={size} color={color} />
  if (t === 'tool') return <Wrench size={size} color={color} />
  if (t.includes('model') || t.includes('llm')) return <Sparkles size={size} color={color} />
  return <Bot size={size} color={color} />
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    width: '360px',
    background: '#1E293B',
    borderLeft: '1px solid #334155',
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
    borderBottom: '1px solid #334155',
  },
  headerTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#F0F4F8',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    marginRight: '8px',
  },
  closeButton: {
    background: 'transparent',
    border: 'none',
    color: '#78909C',
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
    color: '#F0F4F8',
    marginBottom: '10px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 0',
    fontSize: '13px',
  },
  rowLabel: {
    color: '#78909C',
  },
  rowValue: {
    color: '#F0F4F8',
    fontWeight: 600,
    fontVariantNumeric: 'tabular-nums',
    fontFamily: "'JetBrains Mono', monospace",
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
    color: '#78909C',
    width: '32px',
    flexShrink: 0,
  },
  latencyTrack: {
    flex: 1,
    height: '6px',
    background: '#334155',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  latencyFill: {
    height: '100%',
    borderRadius: '3px',
  },
  latencyValue: {
    color: '#F0F4F8',
    fontSize: '12px',
    fontVariantNumeric: 'tabular-nums',
    width: '56px',
    textAlign: 'right' as const,
    flexShrink: 0,
  },
  errorItem: {
    padding: '8px 10px',
    background: 'rgba(255, 82, 82, 0.08)',
    border: '1px solid rgba(255, 82, 82, 0.3)',
    borderRadius: '6px',
    marginBottom: '6px',
    fontSize: '12px',
  },
  errorMessage: {
    color: '#FF5252',
    wordBreak: 'break-word' as const,
    marginBottom: '2px',
  },
  errorCount: {
    color: '#78909C',
    fontSize: '11px',
  },
  spinner: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    color: '#78909C',
    fontSize: '14px',
  },
  errorBox: {
    padding: '12px',
    background: 'rgba(255, 82, 82, 0.08)',
    border: '1px solid rgba(255, 82, 82, 0.3)',
    borderRadius: '6px',
    color: '#FF5252',
    fontSize: '13px',
  },
  cardBlock: {
    background: '#0F172A',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '16px',
  },
  highlightBlock: {
    background: 'rgba(6, 182, 212, 0.05)',
    border: '1px solid rgba(6, 182, 212, 0.2)',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '16px',
  }
}

export default function SidePanel({
  selected,
  projectId,
  hours,
  onClose,
  viewMode = 'topology',
  sparklineData,
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <NodeTypeIcon nodeType={nodeDetail.nodeType} color="#06B6D4" size={20} />
              <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{nodeDetail.label}</span>
            </div>
          )}
          {selected?.kind === 'edge' && edgeDetail && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{edgeDetail.sourceId}</span>
              <ArrowRight size={16} color="#78909C" />
              <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{edgeDetail.targetId}</span>
            </div>
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
          <NodeDetailView
            detail={nodeDetail}
            viewMode={viewMode}
            sparklineData={sparklineData}
          />
        )}

        {edgeDetail && !loading && !error && (
          <EdgeDetailView detail={edgeDetail} />
        )}
      </div>
    </div>
  )
}

function NodeDetailView({
  detail,
  viewMode = 'topology',
  sparklineData,
}: {
  detail: NodeDetail
  viewMode?: ViewMode
  sparklineData?: TimeSeriesData | null
}) {
  const errColor = errorRateColor(detail.errorRate)
  const maxLatency = detail.latency.p99 || 1

  // Resolve sparkline points for this node
  const nodePoints = sparklineData?.series[detail.nodeId]
  const hasSparkline = nodePoints && nodePoints.length >= 2

  return (
    <>
      <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
        <div style={{ ...styles.cardBlock, flex: 1, marginBottom: 0 }}>
          <div style={{ fontSize: '11px', color: '#78909C', marginBottom: '8px' }}>Type</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#F0F4F8', fontWeight: 600 }}>
            <NodeTypeIcon nodeType={detail.nodeType} color="#06B6D4" size={16} />
            {detail.nodeType === 'llm' ? 'Model' : (detail.nodeType.charAt(0).toUpperCase() + detail.nodeType.slice(1))}
          </div>
        </div>
      </div>

      <div style={styles.highlightBlock}>
        <div style={{ fontSize: '11px', color: '#06B6D4', marginBottom: '8px' }}>Total Tokens</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#F0F4F8', fontSize: '24px', fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>
          <Database size={20} color="#06B6D4" />
          {formatTokens(detail.inputTokens + detail.outputTokens)}
        </div>
      </div>

      <div style={styles.cardBlock}>
        <div style={styles.sectionTitle}><Hash size={14} /> Token Breakdown</div>
        <div style={{ paddingLeft: '20px' }}>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Input Tokens</span>
            <span style={styles.rowValue}>{formatTokens(detail.inputTokens)}</span>
          </div>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Output Tokens</span>
            <span style={styles.rowValue}>{formatTokens(detail.outputTokens)}</span>
          </div>
          <div style={{ height: '1px', background: '#334155', margin: '8px 0' }}></div>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Estimated Cost</span>
            <span style={{ ...styles.rowValue, color: '#34D399' }}>{formatCost(detail.estimatedCost)}</span>
          </div>
        </div>
      </div>

      <div style={styles.cardBlock}>
        <div style={styles.sectionTitle}><Activity size={14} /> Invocations & Performance</div>
        <div style={{ paddingLeft: '20px' }}>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Total Executions</span>
            <span style={styles.rowValue}>{detail.totalInvocations.toLocaleString()}</span>
          </div>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Error Rate</span>
            <span style={{ ...styles.badge, color: '#fff', background: errColor }}>
              {detail.errorRate.toFixed(1)}%
            </span>
          </div>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Error Count</span>
            <span style={{ ...styles.rowValue, color: detail.errorCount > 0 ? '#FF5252' : '#F0F4F8' }}>
              {detail.errorCount.toLocaleString()}
            </span>
          </div>

          <div style={{ height: '1px', background: '#334155', margin: '12px 0' }}></div>
          <div style={{ fontSize: '11px', color: '#78909C', marginBottom: '8px', fontWeight: 600 }}>LATENCY PERCENTILES</div>
          {(['p50', 'p95', 'p99'] as const).map((pct) => {
            const value = detail.latency[pct]
            const widthPct = maxLatency > 0 ? (value / maxLatency) * 100 : 0
            const barColors: Record<string, string> = {
              p50: '#34D399',
              p95: '#FBBF24',
              p99: '#FF5252',
            }
            return (
              <div key={pct} style={styles.latencyBar}>
                <span style={styles.latencyLabel}>{pct.toUpperCase()}</span>
                <div style={styles.latencyTrack}>
                  <div style={{ ...styles.latencyFill, width: `${Math.min(widthPct, 100)}%`, background: barColors[pct] }} />
                </div>
                <span style={styles.latencyValue}>{formatLatency(value)}</span>
              </div>
            )
          })}
        </div>
      </div>

      {hasSparkline && (
        <div style={{ ...styles.cardBlock, paddingBottom: '16px' }}>
          <div style={styles.sectionTitle}><Clock size={14} /> {sparkLabel(viewMode)} Trend</div>
          <Sparkline
            data={extractSparkSeries(nodePoints, viewMode)}
            color={sparkColor(viewMode)}
            width={320}
            height={40}
          />
        </div>
      )}

      {detail.topErrors.length > 0 && (
        <div style={styles.cardBlock}>
          <div style={{ ...styles.sectionTitle, color: '#FF5252' }}><AlertCircle size={14} /> Top Errors</div>
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

      {/* Raw Payloads */}
      <PayloadAccordion payloads={detail.recentPayloads ?? []} />
    </>
  )
}

function EdgeDetailView({ detail }: { detail: EdgeDetail }) {
  const errColor = errorRateColor(detail.errorRate)

  return (
    <>
      <div style={styles.cardBlock}>
        <div style={styles.sectionTitle}><Activity size={14} /> Call Metrics</div>
        <div style={{ paddingLeft: '20px' }}>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Call Count</span>
            <span style={styles.rowValue}>
              {detail.callCount.toLocaleString()}
            </span>
          </div>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Error Count</span>
            <span style={{ ...styles.rowValue, color: detail.errorCount > 0 ? '#FF5252' : '#F0F4F8' }}>
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
      </div>

      <div style={styles.cardBlock}>
        <div style={styles.sectionTitle}><Clock size={14} /> Performance</div>
        <div style={{ paddingLeft: '20px' }}>
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
      </div>

      <div style={styles.cardBlock}>
        <div style={styles.sectionTitle}><Database size={14} /> Tokens</div>
        <div style={{ paddingLeft: '20px' }}>
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
      </div>
    </>
  )
}

function PayloadAccordion({ payloads }: { payloads: PayloadEntry[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  if (payloads.length === 0) {
    return (
      <div style={styles.cardBlock}>
        <div style={styles.sectionTitle}>Raw Payloads</div>
        <div style={{ fontSize: '13px', color: '#484f58', paddingLeft: '20px' }}>No recent payloads available.</div>
      </div>
    )
  }

  return (
    <div style={styles.cardBlock}>
      <div style={styles.sectionTitle}><FileDigit size={14} /> Raw Payloads ({payloads.length})</div>
      {payloads.map((p, idx) => {
        const isExpanded = expandedIdx === idx
        const timestamp = p.timestamp
          ? new Date(p.timestamp).toLocaleString()
          : 'Unknown time'

        // Determine which fields have data
        const fields: Array<{ label: string; value: string; lang: string }> = []
        if (p.prompt) fields.push({ label: 'Prompt', value: p.prompt, lang: 'json' })
        if (p.completion) fields.push({ label: 'Completion', value: p.completion, lang: 'json' })
        if (p.toolInput) fields.push({ label: 'Tool Input', value: p.toolInput, lang: 'json' })
        if (p.toolOutput) fields.push({ label: 'Tool Output', value: p.toolOutput, lang: 'json' })

        return (
          <div key={p.spanId || idx} style={{ marginBottom: '6px' }}>
            <button
              onClick={() => setExpandedIdx(isExpanded ? null : idx)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 10px',
                background: '#0F172A',
                border: '1px solid #334155',
                borderRadius: isExpanded ? '6px 6px 0 0' : '6px',
                color: '#F0F4F8',
                fontSize: '12px',
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#78909C' }}>
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </span>
                {timestamp}
              </span>
              <span style={{
                fontSize: '11px',
                padding: '1px 6px',
                borderRadius: '8px',
                background: 'rgba(6,182,212,0.15)',
                color: '#06B6D4',
              }}>
                {p.nodeType}
              </span>
            </button>
            {isExpanded && (
              <div style={{
                border: '1px solid #334155',
                borderTop: 'none',
                borderRadius: '0 0 6px 6px',
                background: '#0F172A',
                padding: '8px',
              }}>
                {fields.length === 0 ? (
                  <div style={{ fontSize: '12px', color: '#484f58', padding: '8px' }}>
                    No payload data captured for this span.
                  </div>
                ) : (
                  fields.map((f) => (
                    <div key={f.label} style={{ marginBottom: '8px' }}>
                      <div style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        color: '#78909C',
                        marginBottom: '4px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>
                        {f.label}
                      </div>
                      <SyntaxHighlighter
                        language={f.lang}
                        style={atomOneDark}
                        customStyle={{
                          margin: 0,
                          borderRadius: '4px',
                          fontSize: '11px',
                          maxHeight: '400px',
                          overflow: 'auto',
                        }}
                        wrapLongLines
                      >
                        {tryFormatJson(f.value)}
                      </SyntaxHighlighter>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

/** Try to parse and pretty-print JSON, fallback to raw string. */
function tryFormatJson(value: string): string {
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
}
