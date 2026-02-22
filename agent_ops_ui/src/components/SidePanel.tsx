import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import sql from 'react-syntax-highlighter/dist/esm/languages/hljs/sql'
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs'
import type { SelectedElement, NodeDetail, EdgeDetail, PayloadEntry, ViewMode, TimeSeriesData, SpanDetails, TraceLogsData, SpanDetailsException, TraceLog, GraphFilters } from '../types'
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
  Clock,
  ExternalLink,
  Copy,
  Check
} from 'lucide-react'
SyntaxHighlighter.registerLanguage('sql', sql)

interface SidePanelProps {
  selected: SelectedElement | null
  projectId: string
  hours: number
  onClose: () => void
  viewMode?: ViewMode
  sparklineData?: TimeSeriesData | null
  filters?: GraphFilters
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
    zIndex: 500,
    display: 'flex',
    flexDirection: 'column',
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
  filters,
}: SidePanelProps) {
  const [nodeDetail, setNodeDetail] = useState<NodeDetail | null>(null)
  const [edgeDetail, setEdgeDetail] = useState<EdgeDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [panelWidth, setPanelWidth] = useState(360)
  const [isResizing, setIsResizing] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (nodeDetail && nodeDetail.errorCount > 0 && panelWidth < 600) {
      setPanelWidth(600)
    }
  }, [nodeDetail, panelWidth])

  // Resize Handlers
  const startResizing = useCallback((e: React.MouseEvent) => {
    setIsResizing(true)
    e.preventDefault()
  }, [])

  const stopResizing = useCallback(() => {
    setIsResizing(false)
  }, [])

  const resize = useCallback((e: MouseEvent) => {
    if (isResizing && panelRef.current) {
      const newWidth = window.innerWidth - e.clientX
      // Set min and max bounds
      if (newWidth >= 300 && newWidth <= Math.min(1200, window.innerWidth - 50)) {
        setPanelWidth(newWidth)
      }
    }
  }, [isResizing])

  useEffect(() => {
    if (isResizing) {
      document.body.style.cursor = 'ew-resize'
      window.addEventListener('mousemove', resize)
      window.addEventListener('mouseup', stopResizing)
    } else {
      document.body.style.cursor = ''
    }
    return () => {
      window.removeEventListener('mousemove', resize)
      window.removeEventListener('mouseup', stopResizing)
    }
  }, [isResizing, resize, stopResizing])

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

    const params = {
      project_id: projectId,
      hours,
      errors_only: !!filters?.errorsOnly,
      trace_dataset: filters?.traceDataset,
      service_name: filters?.serviceName,
    }

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
          if (axios.isAxiosError(err) && err.response?.data?.detail) {
            const detail = err.response.data.detail
            setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
          } else {
            setError(err instanceof Error ? err.message : 'Failed to load details')
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [selected, projectId, hours, filters?.errorsOnly, filters?.traceDataset, filters?.serviceName])

  const isOpen = selected !== null

  return (
    <div
      ref={panelRef}
      style={{
        ...styles.overlay,
        width: `${panelWidth}px`,
        transform: isOpen ? 'translateX(0)' : `translateX(${panelWidth}px)`,
        pointerEvents: isOpen ? 'auto' : 'none',
        transition: isResizing ? 'none' : 'transform 0.25s ease-in-out',
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: '5px',
          cursor: 'ew-resize',
          zIndex: 60,
          background: isResizing ? '#06B6D4' : 'transparent',
          transition: 'background 0.2s',
        }}
        onMouseDown={startResizing}
        onMouseEnter={(e) => { if (!isResizing) e.currentTarget.style.background = 'rgba(6, 182, 212, 0.3)' }}
        onMouseLeave={(e) => { if (!isResizing) e.currentTarget.style.background = 'transparent' }}
      />
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
            projectId={projectId}
            viewMode={viewMode}
            sparklineData={sparklineData}
            filters={filters}
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
  projectId,
  viewMode = 'topology',
  sparklineData,
  filters,
}: {
  detail: NodeDetail
    projectId: string
  viewMode?: ViewMode
  sparklineData?: TimeSeriesData | null
    filters?: GraphFilters
}) {
  const [computedErrors, setComputedErrors] = useState<Array<{ message: string, count: number }>>([])

  // Only use computed errors if they exist, otherwise fallback to generic DB Top Errors
  const displayErrors = computedErrors.length > 0 ? computedErrors.slice(0, 3) : detail.topErrors

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
        {(detail.nodeType === 'agent' || detail.nodeType === 'sub_agent') && (
          <button
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              background: 'rgba(6, 182, 212, 0.1)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              borderRadius: '6px',
              color: '#06B6D4',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              height: 'fit-content',
            }}
            onClick={() => {
              // Open Cloud Trace or whatever is the traces route
              window.open(`https://console.cloud.google.com/traces/list?project=${projectId}`, '_blank')
            }}
          >
            <ExternalLink size={14} />
            View Traces
          </button>
        )}
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

      {(hasSparkline || displayErrors.length > 0) && (
        <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
          {hasSparkline && (
            <div style={{ ...styles.cardBlock, flex: 1, marginBottom: 0, paddingBottom: '16px' }}>
              <div style={styles.sectionTitle}><Clock size={14} /> {sparkLabel(viewMode)} Trend</div>
              <Sparkline
                data={extractSparkSeries(nodePoints, viewMode)}
                color={sparkColor(viewMode)}
                width={140}
                height={40}
              />
            </div>
          )}

          {displayErrors.length > 0 && (
            <div style={{ ...styles.cardBlock, flex: 2, marginBottom: 0 }}>
              <div style={{ ...styles.sectionTitle, color: '#FF5252' }}><AlertCircle size={14} /> Top Errors</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {displayErrors.map((err, idx) => (
                  <div key={idx} style={{ ...styles.errorItem, padding: '4px 8px', marginBottom: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ ...styles.errorMessage, fontSize: '11px', marginBottom: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flex: 1 }}>{err.message}</div>
                    <div style={{ ...styles.errorCount, marginLeft: '8px', flexShrink: 0 }}>
                      {err.count.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <PayloadAccordion
        payloads={detail.recentPayloads ?? []}
        projectId={projectId}
        filters={filters}
        onComputedErrors={setComputedErrors}
      />
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

function PayloadAccordion({
  payloads,
  projectId,
  filters,
  onComputedErrors,
}: {
  payloads: PayloadEntry[]
  projectId: string
  filters?: GraphFilters
    onComputedErrors?: (errors: Array<{ message: string, count: number }>) => void
}) {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())
  const [spanDetailsCache, setSpanDetailsCache] = useState<Record<string, SpanDetails>>({})
  const [traceLogsCache, setTraceLogsCache] = useState<Record<string, TraceLogsData>>({})
  const [loadingIds, setLoadingIds] = useState<Set<number>>(new Set())

  // Pre-fetch all span details on load
  useEffect(() => {
    if (!payloads.length) return

    let isMounted = true

    const prefix = async () => {
      const newLoadingIds = new Set<number>()
      const needsFetch: { p: PayloadEntry, idx: number }[] = []

      payloads.forEach((p, idx) => {
        if (p.traceId && p.spanId && !spanDetailsCache[p.spanId]) {
          newLoadingIds.add(idx)
          needsFetch.push({ p, idx })
        }
      })

      if (needsFetch.length > 0) {
        setLoadingIds(prev => new Set([...prev, ...newLoadingIds]))

        const newlyFetchedDetails: Record<string, SpanDetails> = {}
        const newlyFetchedLogs: Record<string, TraceLogsData> = {}
        const errorCounts: Record<string, number> = {}

        await Promise.all(needsFetch.map(async ({ p }) => {
          try {
            const spanRes = await axios.get(`/api/v1/graph/trace/${p.traceId}/span/${p.spanId}/details`, {
              params: {
                project_id: projectId,
                trace_dataset: filters?.traceDataset,
              }
            })
            newlyFetchedDetails[p.spanId!] = spanRes.data

            // Build error occurrences map
            if (spanRes.data.exceptions && spanRes.data.exceptions.length > 0) {
              spanRes.data.exceptions.forEach((exc: SpanDetailsException) => {
                const msg = `${exc.type}: ${exc.message}`.substring(0, 100)
                errorCounts[msg] = (errorCounts[msg] || 0) + 1
              })
            }
          } catch (e) {
            console.error("Failed to fetch span details", e)
          }

          try {
            if (!traceLogsCache[p.traceId!]) {
              const logsRes = await axios.get(`/api/v1/graph/trace/${p.traceId}/logs`, {
                params: {
                  project_id: projectId,
                  trace_dataset: filters?.traceDataset,
                }
              })
              newlyFetchedLogs[p.traceId!] = logsRes.data
            }
          } catch (e) {
            console.error("Failed to fetch trace logs", e)
          }
        }))

        if (isMounted) {
          setSpanDetailsCache(prev => ({ ...prev, ...newlyFetchedDetails }))
          setTraceLogsCache(prev => ({ ...prev, ...newlyFetchedLogs }))
          setLoadingIds(prev => {
            const next = new Set(prev)
            needsFetch.forEach(({ idx }) => next.delete(idx))
            return next
          })

          if (Object.keys(errorCounts).length > 0 && onComputedErrors) {
            const errArray = Object.entries(errorCounts)
              .map(([message, count]) => ({ message, count }))
              .sort((a, b) => b.count - a.count)
            onComputedErrors(errArray)
          }
        }
      }
    }

    prefix()
    return () => { isMounted = false }
  }, [payloads, projectId, filters, onComputedErrors, spanDetailsCache, traceLogsCache])


  if (payloads.length === 0) {
    return (
      <div style={styles.cardBlock}>
        <div style={styles.sectionTitle}>Error Details</div>
        <div style={{ fontSize: '13px', color: '#484f58', paddingLeft: '20px' }}>No recent payloads available.</div>
      </div>
    )
  }

  const handleToggle = (idx: number) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  return (
    <div style={styles.cardBlock}>
      <div style={styles.sectionTitle}><FileDigit size={14} /> Error Details ({payloads.length})</div>
      {payloads.map((p, idx) => {
        const isExpanded = expandedIds.has(idx)
        const timestamp = p.timestamp
          ? new Date(p.timestamp).toLocaleString()
          : 'Unknown time'

        // Determine which fields have data
        const fields: Array<{ label: string; value: string; lang: string }> = []
        if (p.prompt) fields.push({ label: 'Prompt', value: p.prompt, lang: 'json' })
        if (p.completion) fields.push({ label: 'Completion', value: p.completion, lang: 'json' })
        if (p.toolInput) fields.push({ label: 'Tool Input', value: p.toolInput, lang: 'json' })
        if (p.toolOutput) fields.push({ label: 'Tool Output', value: p.toolOutput, lang: 'json' })

        const spanDetails = spanDetailsCache[p.spanId]
        const traceLogs = p.traceId ? traceLogsCache[p.traceId] : null
        const exceptions = spanDetails?.exceptions || []
        const logs = traceLogs?.logs || []
        const isLoadingExtras = loadingIds.has(idx)

        return (
          <div key={p.spanId || idx} style={{ marginBottom: '6px' }}>
            <button
              onClick={() => handleToggle(idx)}
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
                {isLoadingExtras && (
                  <div style={{ fontSize: '12px', color: '#78909C', padding: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    Loading error details...
                  </div>
                )}

                {exceptions.length > 0 && (
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#FF5252', marginBottom: '8px' }}>
                      <AlertCircle size={12} style={{ marginRight: '4px', verticalAlign: '-2px' }} />
                      EXCEPTIONS
                    </div>
                    {exceptions.map((exc: SpanDetailsException, i: number) => (
                      <div key={i} style={{ background: 'rgba(255, 82, 82, 0.08)', border: '1px solid rgba(255, 82, 82, 0.3)', borderRadius: '4px', padding: '8px', marginBottom: '8px', position: 'relative' }}>
                        <div style={{ position: 'absolute', top: '8px', right: '8px' }}>
                          <CopyButton text={exc.stacktrace || exc.message} />
                        </div>
                        <div style={{ color: '#FF5252', fontSize: '12px', fontWeight: 600, marginBottom: '4px', paddingRight: '24px' }}>{exc.type}: {exc.message}</div>
                        {exc.stacktrace && (
                          <SyntaxHighlighter
                            language="python"
                            style={atomOneDark}
                            customStyle={{ margin: 0, borderRadius: '4px', fontSize: '11px', maxHeight: '200px', overflow: 'auto' }}
                          >
                            {exc.stacktrace}
                          </SyntaxHighlighter>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {logs.length > 0 && (
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#FBBF24', marginBottom: '8px' }}>
                      TRACE LOGS
                    </div>
                    <div style={{ background: '#1E293B', borderRadius: '4px', padding: '8px', maxHeight: '200px', overflow: 'auto' }}>
                      {logs.map((log: TraceLog, i: number) => {
                        let payloadStr = log.payload;
                        if (typeof payloadStr === 'object') {
                          payloadStr = JSON.stringify(payloadStr, null, 2);
                        }
                        const color = log.severity === 'ERROR' || log.severity === 'CRITICAL' ? '#FF5252' : '#F0F4F8';
                        return (
                          <div key={i} style={{ marginBottom: '6px', fontSize: '11px', color }}>
                            <span style={{ color: '#78909C', marginRight: '8px' }}>
                              [{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Unknown'}]
                            </span>
                            {String(payloadStr)}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

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
                      <div style={{ position: 'relative' }}>
                        <div style={{ position: 'absolute', top: '8px', right: '8px', zIndex: 10 }}>
                          <CopyButton text={tryFormatJson(f.value)} />
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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      title="Copy to clipboard"
      style={{
        background: 'rgba(255, 255, 255, 0.1)',
        border: 'none',
        borderRadius: '4px',
        color: copied ? '#34D399' : '#78909C',
        padding: '5px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'color 0.2s, background 0.2s',
      }}
      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)'}
      onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'}
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  )
}
