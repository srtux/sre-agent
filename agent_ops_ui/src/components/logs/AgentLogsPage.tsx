import { useMemo, useState, useEffect } from 'react'
import { useAgentLogs, useLogsHistogram, buildFilter } from '../../hooks/useAgentLogs'
import { useAgentContext } from '../../contexts/AgentContext'
import { Search, RotateCcw } from 'lucide-react'
import LogsHistogram from './LogsHistogram'
import VirtualLogTable from './VirtualLogTable'
import Editor from 'react-simple-code-editor'
import Prism from 'prismjs'
import 'prismjs/components/prism-core'
import 'prismjs/components/prism-clike'
import 'prismjs/components/prism-javascript'
import 'prismjs/themes/prism-tomorrow.css'

// Custom logging filter grammar for Prism based on typical GCP structures + keywords
Prism.languages.logquery = {
  keyword: /\b(AND|OR|NOT)\b/i,
  string: /(["'])(?:\\(?:\r\n|[\s\S])|(?!\1)[^\\\r\n])*\1/,
  property: /\b[a-zA-Z_][a-zA-Z0-9_\.]*\b(?=\s*(=|!=|>=|<=|>|<|:))/,
  operator: /=|!=|>=|<=|>|<|:/,
  boolean: /\b(true|false)\b/i,
  number: /\b\d+(?:\.\d+)?\b/
}

interface AgentLogsPageProps {
  /** Time range in hours from the top-level filter */
  hours: number
  /** Severity filter from the top-level toolbar (e.g. ['ERROR','WARNING']). Empty = all. */
  severity?: string[]
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    width: '100%',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    overflow: 'hidden',
    padding: '12px',
    boxSizing: 'border-box',
    gap: '12px',
  },
  skeleton: {
    background: 'linear-gradient(90deg, #1E293B 25%, #334155 50%, #1E293B 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s infinite',
    borderRadius: '8px',
  },
  empty: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    color: '#475569',
    fontSize: '14px',
  },
  emptyIcon: {
    fontSize: '32px',
    opacity: 0.5,
  },
  statsBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    fontSize: '12px',
    color: '#78909C',
  },
  queryBar: {
    display: 'flex',
    gap: '8px',
    background: '#0F172A',
    padding: '8px',
    borderRadius: '8px',
    border: '1px solid #334155',
    alignItems: 'flex-start',
  },
  searchInput: {
    flex: 1,
    background: 'transparent',
    color: '#E2E8F0',
    fontSize: '13px',
    fontFamily: "'JetBrains Mono', monospace",
    minHeight: '36px',
    border: 'none',
  },
  actionButton: {
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '4px',
    padding: '4px 8px',
    color: '#94A3B8',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    transition: 'all 0.2s',
  },
}

// Inject shimmer animation
const SHIMMER_ID = '__logs-shimmer-keyframe'
if (typeof document !== 'undefined' && !document.getElementById(SHIMMER_ID)) {
  const el = document.createElement('style')
  el.id = SHIMMER_ID
  el.textContent = '@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }'
  document.head.appendChild(el)
}

/** Convert hours to minutes for the API. */
function hoursToMinutes(hours: number): number {
  return Math.round(hours * 60)
}

export default function AgentLogsPage({ hours, severity = [] }: AgentLogsPageProps) {
  const { projectId, serviceName, availableAgents } = useAgentContext()
  const minutesAgo = hoursToMinutes(hours)

  // Map serviceName from top-level agent selector to reasoning_engine_id for the filter.
  // We find the agent in the registry to get its actual engine ID.
  const selectedAgentId = useMemo(() => {
    if (!serviceName || serviceName === 'all') return 'all'
    const agent = availableAgents.find((a) => a.serviceName === serviceName)
    // Preference actual engine mapping first, but fallback to serviceName for standalone containers
    return agent?.engineId || agent?.agentId || serviceName
  }, [serviceName, availableAgents])

  const initialFilter = useMemo(() => {
    return buildFilter({
      agentId: selectedAgentId,
      severity,
      projectId,
      minutesAgo,
    })
  }, [selectedAgentId, severity, projectId, minutesAgo])

  const [queryText, setQueryText] = useState(initialFilter)
  const [activeFilter, setActiveFilter] = useState(initialFilter)

  // Update query text when dropdown filters change
  useEffect(() => {
    setQueryText(initialFilter)
    setActiveFilter(initialFilter)
  }, [initialFilter])

  const handleLoad = () => {
    setActiveFilter(queryText)
  }

  const logsQuery = useAgentLogs({
    agentId: selectedAgentId,
    severity,
    projectId,
    minutesAgo,
    filterOverride: activeFilter,
  })
  const histoQuery = useLogsHistogram({
    agentId: selectedAgentId,
    severity,
    projectId,
    minutesAgo,
    filterOverride: activeFilter,
  })

  const entries = useMemo(
    () => logsQuery.data?.pages.flatMap((p) => p.entries) ?? [],
    [logsQuery.data],
  )

  const totalLoaded = entries.length
  const histoBuckets = histoQuery.data?.buckets ?? []
  const histoTotal = histoQuery.data?.total_count ?? 0

  const isInitialLoad = logsQuery.isLoading && !logsQuery.data

  return (
    <div style={styles.container}>
      {/* Query box */}
      <div style={styles.queryBar}>
        <Search size={16} color="#475569" style={{ marginTop: '8px' }} />
        <div style={styles.searchInput}>
          <Editor
            value={queryText}
            onValueChange={setQueryText}
            highlight={(code) => Prism.highlight(code, Prism.languages.logquery, 'logquery')}
            padding={{ top: 6, bottom: 6, left: 4, right: 4 }}
            placeholder='Filter logs (e.g. severity="ERROR" AND textPayload:timeout)'
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '13px',
              backgroundColor: 'transparent',
              outline: 'none',
              minHeight: '32px',
            }}
            textareaClassName="log-query-textarea"
            onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement | HTMLDivElement>) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleLoad()
              }
            }}
          />
        </div>
        <button
          onClick={handleLoad}
          disabled={logsQuery.isFetching}
          style={styles.actionButton}
          onMouseOver={(e) => {
            if (!logsQuery.isFetching) e.currentTarget.style.borderColor = '#06B6D4'
          }}
          onMouseOut={(e) => {
            if (!logsQuery.isFetching) e.currentTarget.style.borderColor = '#334155'
          }}
        >
          {logsQuery.isFetching ? 'Loading...' : 'Run'}
        </button>
        <button
          onClick={() => {
            setQueryText(initialFilter)
            setActiveFilter(initialFilter)
          }}
          title="Reset to default filters"
          style={{ ...styles.actionButton, padding: '4px' }}
          onMouseOver={(e) => (e.currentTarget.style.borderColor = '#06B6D4')}
          onMouseOut={(e) => (e.currentTarget.style.borderColor = '#334155')}
        >
          <RotateCcw size={14} />
        </button>
      </div>

      {/* Stats bar */}
      <div style={{ ...styles.statsBar, padding: '4px 16px' }}>
        <span>
          {histoTotal > 0
            ? `${histoTotal.toLocaleString()} entries scanned`
            : isInitialLoad
              ? 'Loading...'
              : 'No entries'}
        </span>
        {totalLoaded > 0 && <span>{totalLoaded.toLocaleString()} loaded</span>}
        {activeFilter !== queryText && (
          <span style={{ color: '#FACC15', marginLeft: 'auto', fontSize: '11px' }}>
            Query changed. Click Load to refresh.
          </span>
        )}
      </div>

      {/* Histogram */}
      {isInitialLoad ? (
        <div style={{ ...styles.skeleton, height: '160px', flexShrink: 0 }} />
      ) : (
        <LogsHistogram
          buckets={histoBuckets}
          loading={histoQuery.isLoading}
        />
      )}

      {/* Error state */}
      {(logsQuery.isError || histoQuery.isError) && (
        <div style={{ ...styles.empty, color: '#F87171', flex: 'none', padding: '12px 0' }}>
          <span>Failed to load logs. Check your connection and try again.</span>
        </div>
      )}

      {/* Log table */}
      {isInitialLoad ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '8px', padding: '0 16px' }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} style={{ ...styles.skeleton, height: '36px' }} />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <div style={styles.empty}>
          <span style={styles.emptyIcon}>No log entries found</span>
          <span>Try adjusting your filters or time range.</span>
        </div>
      ) : (
        <VirtualLogTable
          entries={entries}
          hasNextPage={!!logsQuery.hasNextPage}
          isFetchingNextPage={logsQuery.isFetchingNextPage}
          fetchNextPage={() => logsQuery.fetchNextPage()}
        />
      )}
    </div>
  )
}
