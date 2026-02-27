import React from 'react'
import { useSessionTrajectory } from '../../hooks/useSessionTrajectory'

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '8px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    height: '100%',
    overflowY: 'auto',
    background: '#0F172A',
    fontFamily: "'JetBrains Mono', monospace",
  },
  eventCard: {
    background: 'rgba(30, 41, 59, 0.4)',
    border: '1px solid rgba(51, 65, 85, 0.5)',
    borderRadius: '6px',
    padding: '8px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  eventHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
    paddingBottom: '4px',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  nodeTypeLabel: {
    padding: '1px 6px',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: 600,
    textTransform: 'uppercase',
  },
  nodeLabel: {
    fontSize: '12px',
    fontWeight: 500,
    color: '#F8FAFC',
  },
  metaText: {
    fontSize: '11px',
    color: '#64748B',
  },
  contentSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px', // Compact
  },
  sectionHeading: {
    fontSize: '10px',
    fontWeight: 600,
    color: '#94A3B8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '2px',
  },
  codeBlock: {
    background: '#020617',
    padding: '6px 8px',
    borderRadius: '4px',
    border: '1px solid rgba(255,255,255,0.05)',
    color: '#cbd5e1',
    whiteSpace: 'pre-wrap',
    overflowX: 'auto',
    fontSize: '10px',
    maxHeight: '150px',
    overflowY: 'auto',
  },
  logRow: {
    display: 'flex',
    gap: '8px',
    padding: '2px 0',
    borderBottom: '1px solid rgba(255,255,255,0.02)',
    fontSize: '10px',
  },
  logTime: {
    color: '#64748B',
    whiteSpace: 'nowrap',
  },
  logSev: {
    fontWeight: 600,
    width: '50px',
  },
  logPayload: {
    color: '#cbd5e1',
    wordBreak: 'break-word',
  },
  evalChip: {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: '8px',
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
  }
}

interface Props {
  sessionId: string | null
  activeTab: string
  viewMode: string
}

function getNodeTypeColor(type: string): string {
  if (type === 'LLM' || type.includes('Agent')) return '#818CF8'
  if (type === 'Tool') return '#34D399'
  return '#94A3B8'
}

function getNodeTypeBg(type: string): string {
  if (type === 'LLM' || type.includes('Agent')) return 'rgba(129, 140, 248, 0.15)'
  if (type === 'Tool') return 'rgba(52, 211, 153, 0.15)'
  return 'rgba(148, 163, 184, 0.15)'
}

function formatJsonStr(jsonStr: string): string {
  try {
    const obj = JSON.parse(jsonStr)
    return JSON.stringify(obj, null, 2)
  } catch {
    return jsonStr
  }
}

export const SessionLogsView: React.FC<Props> = ({ sessionId, activeTab, viewMode }) => {
  const { data, loading, error } = useSessionTrajectory(sessionId, activeTab, viewMode)

  if (!sessionId) {
    return <div style={{ padding: 24, color: '#94a3b8' }}>Select a session to view its trajectory logs.</div>
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '100px 0' }}>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
        <div style={styles.spinner} />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24, color: '#EF4444', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Error loading trajectory</h3>
        <p style={{ margin: 0 }}>{error.message || 'An unknown error occurred'}</p>
      </div>
    )
  }

  const trajectory = data?.trajectory || []

  if (trajectory.length === 0) {
    return <div style={{ padding: 24, color: '#94a3b8' }}>No trajectory data found for this session.</div>
  }

  return (
    <div style={styles.container}>
      {trajectory.map((event, idx) => {
        const d = event.startTime ? new Date(event.startTime) : null
        const timeStr = d ? d.toLocaleTimeString() : '-'

        const typeColor = getNodeTypeColor(event.nodeType)
        const typeBg = getNodeTypeBg(event.nodeType)

        return (
          <div key={event.spanId || idx} style={styles.eventCard}>
            <div style={styles.eventHeader}>
              <div style={styles.headerLeft}>
                <span style={{
                  ...styles.nodeTypeLabel,
                  color: typeColor,
                  backgroundColor: typeBg,
                  border: `1px solid ${typeColor}40`
                }}>
                  {event.nodeType}
                </span>
                <span style={styles.nodeLabel}>{event.nodeLabel || 'Unnamed Node'}</span>
                {event.durationMs > 0 && (
                  <span style={styles.metaText}>{event.durationMs.toFixed(0)} ms</span>
                )}
              </div>
              <div style={styles.metaText}>{timeStr}</div>
            </div>

            {/* Content Payload */}
            {(event.systemMessage || event.prompt || event.completion || event.toolInput || event.toolOutput) && (
              <div style={styles.contentSection}>
                {event.prompt && (
                  <div>
                    <div style={styles.sectionHeading}>Input / Prompt</div>
                    <div style={styles.codeBlock}>{formatJsonStr(event.prompt)}</div>
                  </div>
                )}
                {event.toolInput && (
                  <div>
                    <div style={styles.sectionHeading}>Tool Input</div>
                    <div style={styles.codeBlock}>{formatJsonStr(event.toolInput)}</div>
                  </div>
                )}
                {event.completion && (
                  <div>
                    <div style={styles.sectionHeading}>Output / Completion</div>
                    <div style={styles.codeBlock}>{formatJsonStr(event.completion)}</div>
                  </div>
                )}
                {event.toolOutput && (
                  <div>
                    <div style={styles.sectionHeading}>Tool Output</div>
                    <div style={styles.codeBlock}>{formatJsonStr(event.toolOutput)}</div>
                  </div>
                )}
              </div>
            )}

            {/* Evaluations */}
            {event.evaluations && event.evaluations.length > 0 && (
              <div style={styles.contentSection}>
                <div style={styles.sectionHeading}>Evaluations</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {event.evaluations.map((ev, i) => {
                    const isGood = ev.score >= 0.8
                    const isWarn = ev.score >= 0.5 && ev.score < 0.8
                    const color = isGood ? '#10B981' : isWarn ? '#F59E0B' : '#EF4444'
                    const bg = isGood ? 'rgba(16, 185, 129, 0.1)' : isWarn ? 'rgba(245, 158, 11, 0.1)' : 'rgba(239, 68, 68, 0.1)'
                    return (
                      <span key={i} title={ev.explanation} style={{ ...styles.evalChip, color, backgroundColor: bg, border: `1px solid ${color}40` }}>
                        {ev.metricName}: {ev.score.toFixed(2)}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Logs */}
            {event.logs && event.logs.length > 0 && (
              <div style={styles.contentSection}>
                <div style={styles.sectionHeading}>Correlated Logs ({event.logs.length})</div>
                <div style={{ ...styles.codeBlock, background: 'rgba(0,0,0,0.3)', padding: '4px 8px' }}>
                  {event.logs.map((log, i) => {
                    const ld = log.timestamp ? new Date(log.timestamp) : null
                    const ltimeStr = ld ? `${ld.getHours().toString().padStart(2, '0')}:${ld.getMinutes().toString().padStart(2, '0')}:${ld.getSeconds().toString().padStart(2, '0')}` : '-'
                    const sev = log.severity || 'INFO'
                    let sevColor = '#38BDF8'
                    if (sev === 'WARNING') sevColor = '#FACC15'
                    if (sev === 'ERROR') sevColor = '#F87171'

                    let payloadStr = ""
                    if (typeof log.payload === 'string') payloadStr = log.payload
                    else payloadStr = JSON.stringify(log.payload, null, 2)

                    return (
                      <div key={i} style={styles.logRow}>
                        <div style={styles.logTime}>{ltimeStr}</div>
                        <div style={{ ...styles.logSev, color: sevColor }}>{sev}</div>
                        <div style={styles.logPayload}>{payloadStr}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

          </div>
        )
      })}
    </div>
  )
}
