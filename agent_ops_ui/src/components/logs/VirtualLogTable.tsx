import { useRef, useState, useEffect, useCallback } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import json from 'react-syntax-highlighter/dist/esm/languages/hljs/json'
import atomOneDark from 'react-syntax-highlighter/dist/esm/styles/hljs/atom-one-dark'
import type { LogEntry } from '../../types'

SyntaxHighlighter.registerLanguage('json', json)

const SEVERITY_COLORS: Record<string, string> = {
  DEBUG: '#64748B',
  DEFAULT: '#64748B',
  INFO: '#38BDF8',
  NOTICE: '#38BDF8',
  WARNING: '#FACC15',
  ERROR: '#F87171',
  CRITICAL: '#A855F7',
  ALERT: '#A855F7',
  EMERGENCY: '#A855F7',
}

const COLLAPSED_HEIGHT = 36
const EXPANDED_MIN_HEIGHT = 200

interface VirtualLogTableProps {
  entries: LogEntry[]
  hasNextPage: boolean
  isFetchingNextPage: boolean
  fetchNextPage: () => void
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ts

  const pad = (n: number) => String(n).padStart(2, '0')
  const M = pad(d.getMonth() + 1)
  const D = pad(d.getDate())
  const h = pad(d.getHours())
  const m = pad(d.getMinutes())
  const s = pad(d.getSeconds())

  return `${M}-${D} ${h}:${m}:${s}`
}

function getPayloadPreview(entry: LogEntry): string {
  if (typeof entry.payload === 'string') return entry.payload
  if (entry.payload && typeof entry.payload === 'object') {
    const msg = (entry.payload as Record<string, unknown>).message
    if (typeof msg === 'string') return msg
    return JSON.stringify(entry.payload).slice(0, 200)
  }
  return ''
}

function getPayloadFull(entry: LogEntry): string {
  if (typeof entry.payload === 'string') return entry.payload
  if (entry.payload && typeof entry.payload === 'object') {
    return JSON.stringify(entry.payload, null, 2)
  }
  return ''
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    overflow: 'hidden',
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    display: 'grid',
    gridTemplateColumns: '28px 120px 70px 1fr',
    alignItems: 'center',
    padding: '0 12px',
    height: '32px',
    borderBottom: '1px solid #334155',
    background: '#0F172A',
    fontSize: '11px',
    fontWeight: 600,
    color: '#78909C',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    flexShrink: 0,
  },
  scrollArea: {
    flex: 1,
    overflow: 'auto',
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '28px 120px 70px 1fr',
    alignItems: 'center',
    padding: '0 12px',
    height: `${COLLAPSED_HEIGHT}px`,
    borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
    cursor: 'pointer',
    transition: 'background 0.1s',
    fontSize: '12px',
    color: '#B0BEC5',
  },
  severityDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    display: 'inline-block',
  },
  severityBadge: {
    fontSize: '11px',
    fontWeight: 600,
    fontFamily: "'JetBrains Mono', monospace",
  },
  timestamp: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    color: '#78909C',
  },
  preview: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  expandedContent: {
    padding: '8px 12px 12px 52px',
    background: '#0F172A',
    borderBottom: '1px solid #334155',
  },
  metaRow: {
    display: 'flex',
    gap: '16px',
    marginBottom: '8px',
    flexWrap: 'wrap',
  },
  metaItem: {
    fontSize: '11px',
    color: '#78909C',
  },
  metaLabel: {
    color: '#475569',
    marginRight: '4px',
  },
  loadingMore: {
    textAlign: 'center',
    padding: '12px',
    fontSize: '12px',
    color: '#78909C',
  },
}

export default function VirtualLogTable({
  entries,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
}: VirtualLogTableProps) {
  const parentRef = useRef<HTMLDivElement>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const entriesRef = useRef(entries)
  entriesRef.current = entries

  const estimateSize = useCallback(
    (index: number) => {
      const entry = entriesRef.current[index]
      if (!entry) return COLLAPSED_HEIGHT
      if (entry.insert_id === expandedId) return EXPANDED_MIN_HEIGHT
      return COLLAPSED_HEIGHT
    },
    [expandedId],
  )

  const virtualizer = useVirtualizer({
    count: entries.length,
    getScrollElement: () => parentRef.current,
    estimateSize,
    overscan: 20,
  })

  // Infinite scroll: fetch next page when near bottom (throttled via rAF)
  useEffect(() => {
    const el = parentRef.current
    if (!el) return

    let ticking = false
    const handleScroll = () => {
      if (ticking) return
      ticking = true
      requestAnimationFrame(() => {
        const { scrollTop, scrollHeight, clientHeight } = el
        if (scrollHeight - scrollTop - clientHeight < 300 && hasNextPage && !isFetchingNextPage) {
          fetchNextPage()
        }
        ticking = false
      })
    }

    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  const toggleRow = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <span />
        <span>Timestamp</span>
        <span>Severity</span>
        <span>Message</span>
      </div>

      {/* Virtualized rows */}
      <div ref={parentRef} style={styles.scrollArea}>
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            position: 'relative',
            width: '100%',
          }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const entry = entries[virtualRow.index]
            if (!entry) return null
            const isExpanded = expandedId === entry.insert_id
            const sevColor = SEVERITY_COLORS[entry.severity] || '#78909C'

            return (
              <div
                key={virtualRow.key}
                data-index={virtualRow.index}
                ref={virtualizer.measureElement}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {/* Collapsed row */}
                <div
                  style={{
                    ...styles.row,
                    background: isExpanded
                      ? 'rgba(6, 182, 212, 0.05)'
                      : virtualRow.index % 2 === 0
                        ? 'transparent'
                        : 'rgba(15, 23, 42, 0.3)',
                  }}
                  onClick={() => toggleRow(entry.insert_id)}
                  onMouseOver={(e) => {
                    if (!isExpanded) e.currentTarget.style.background = 'rgba(51, 65, 85, 0.3)'
                  }}
                  onMouseOut={(e) => {
                    if (!isExpanded) {
                      e.currentTarget.style.background =
                        virtualRow.index % 2 === 0 ? 'transparent' : 'rgba(15, 23, 42, 0.3)'
                    }
                  }}
                >
                  <span>
                    {isExpanded ? (
                      <ChevronDown size={14} color="#78909C" />
                    ) : (
                      <ChevronRight size={14} color="#475569" />
                    )}
                  </span>
                  <span style={styles.timestamp}>{formatTimestamp(entry.timestamp)}</span>
                  <span style={{ ...styles.severityBadge, color: sevColor }}>
                    <span style={{ ...styles.severityDot, background: sevColor, marginRight: '6px' }} />
                    {entry.severity}
                  </span>
                  <span style={styles.preview}>{getPayloadPreview(entry)}</span>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div style={styles.expandedContent}>
                    {/* Metadata */}
                    <div style={styles.metaRow}>
                      {entry.insert_id && (
                        <span style={styles.metaItem}>
                          <span style={styles.metaLabel}>ID:</span>
                          {entry.insert_id}
                        </span>
                      )}
                      {entry.resource_type && (
                        <span style={styles.metaItem}>
                          <span style={styles.metaLabel}>Resource:</span>
                          {entry.resource_type}
                        </span>
                      )}
                      {entry.trace_id && (
                        <span style={styles.metaItem}>
                          <span style={styles.metaLabel}>Trace:</span>
                          {entry.trace_id}
                        </span>
                      )}
                      {entry.span_id && (
                        <span style={styles.metaItem}>
                          <span style={styles.metaLabel}>Span:</span>
                          {entry.span_id}
                        </span>
                      )}
                    </div>
                    {entry.resource_labels && Object.keys(entry.resource_labels).length > 0 && (
                      <div style={{ ...styles.metaRow, marginBottom: '8px' }}>
                        {Object.entries(entry.resource_labels).map(([k, v]) => (
                          <span key={k} style={styles.metaItem}>
                            <span style={styles.metaLabel}>{k}:</span>
                            {v}
                          </span>
                        ))}
                      </div>
                    )}
                    {/* Full payload / Raw JSON */}
                    {entry.raw ? (
                      <div style={{ marginTop: '12px' }}>
                        <div style={{ ...styles.metaLabel, marginBottom: '4px', fontSize: '10px', textTransform: 'uppercase' }}>Full Log Entry (JSON)</div>
                        <SyntaxHighlighter
                          language="json"
                          style={atomOneDark}
                          customStyle={{
                            margin: 0,
                            padding: '8px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            background: '#0F172A',
                            border: '1px solid #1E293B',
                          }}
                        >
                          {JSON.stringify(entry.raw, null, 2)}
                        </SyntaxHighlighter>
                      </div>
                    ) : typeof entry.payload === 'string' ? (
                      <pre
                        style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: '12px',
                          color: '#B0BEC5',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-all',
                          margin: 0,
                          background: '#0F172A',
                          padding: '8px',
                          borderRadius: '4px',
                          border: '1px solid #1E293B',
                        }}
                      >
                        {entry.payload}
                      </pre>
                    ) : (
                      <SyntaxHighlighter
                        language="json"
                        style={atomOneDark}
                        customStyle={{
                          margin: 0,
                          padding: '8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          background: '#0F172A',
                          border: '1px solid #1E293B',
                        }}
                      >
                        {getPayloadFull(entry)}
                      </SyntaxHighlighter>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {isFetchingNextPage && <div style={styles.loadingMore}>Loading more...</div>}
      </div>
    </div>
  )
}
