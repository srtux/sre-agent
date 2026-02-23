import { useMemo } from 'react'
import { useAgentLogs, useLogsHistogram } from '../../hooks/useAgentLogs'
import { useAgentContext } from '../../contexts/AgentContext'
import LogsHistogram from './LogsHistogram'
import VirtualLogTable from './VirtualLogTable'

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
    padding: '4px 0',
    fontSize: '12px',
    color: '#78909C',
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
  const { projectId, serviceName } = useAgentContext()
  const minutesAgo = hoursToMinutes(hours)

  // Map serviceName from top-level agent selector to agentId for the hook.
  // Empty serviceName = 'all' agents.
  const agentId = serviceName || 'all'

  const logsQuery = useAgentLogs({ agentId, severity, projectId, minutesAgo })
  const histoQuery = useLogsHistogram({ agentId, severity, projectId, minutesAgo })

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
      {/* Stats bar */}
      <div style={styles.statsBar}>
        <span>
          {histoTotal > 0
            ? `${histoTotal.toLocaleString()} entries scanned`
            : isInitialLoad
              ? 'Loading...'
              : 'No entries'}
        </span>
        {totalLoaded > 0 && <span>{totalLoaded.toLocaleString()} loaded</span>}
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
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '8px' }}>
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
