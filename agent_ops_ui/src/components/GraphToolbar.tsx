import type { GraphFilters, AutoRefreshConfig, RefreshInterval } from '../types'

interface GraphToolbarProps {
  filters: GraphFilters
  onChange: (filters: GraphFilters) => void
  onLoad: () => void
  loading: boolean
  autoRefresh: AutoRefreshConfig
  onAutoRefreshChange: (config: AutoRefreshConfig) => void
  lastUpdated: Date | null
}

import TimeRangeSelector from './TimeRangeSelector'
import { useAgentContext } from '../contexts/AgentContext'
import { Bot } from 'lucide-react'

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 24px',
    background: '#1E293B',
    flexWrap: 'wrap',
    borderRadius: '16px',
    margin: '16px 24px',
    border: '1px solid #334155',
  },
  label: {
    fontSize: '13px',
    color: '#78909C',
  },
  input: {
    padding: '6px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '6px',
    color: '#F0F4F8',
    fontSize: '14px',
    outline: 'none',
    width: '220px',
  },
  select: {
    padding: '6px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '6px',
    color: '#F0F4F8',
    fontSize: '14px',
    outline: 'none',
    cursor: 'pointer',
  },
  loadButton: {
    padding: '6px 16px',
    background: '#06B6D4',
    border: '1px solid #06B6D4',
    borderRadius: '6px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  loadButtonDisabled: {
    padding: '6px 16px',
    background: 'rgba(6, 182, 212, 0.3)',
    border: '1px solid rgba(6, 182, 212, 0.3)',
    borderRadius: '6px',
    color: 'rgba(255, 255, 255, 0.54)',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'not-allowed',
  },
  toggleContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
    userSelect: 'none' as const,
  },
  toggleTrack: {
    width: '44px',
    height: '22px',
    borderRadius: '11px',
    position: 'relative' as const,
    transition: 'background 0.2s ease',
  },
  toggleThumb: {
    position: 'absolute' as const,
    top: '3px',
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    background: '#ffffff',
    transition: 'left 0.2s ease',
  },
  toggleLabel: {
    fontSize: '13px',
    transition: 'color 0.2s ease',
  },
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function GraphToolbar({
  filters,
  onChange,
  onLoad,
  loading,
  autoRefresh,
  onAutoRefreshChange,
  lastUpdated,
}: GraphToolbarProps) {
  const { serviceName, setServiceName, availableAgents, loadingAgents } = useAgentContext()
  const canLoad = !loading && filters.projectId.trim().length > 0

  const handleToggle = () => {
    onChange({ ...filters, errorsOnly: !filters.errorsOnly })
  }

  return (
    <div style={styles.bar}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Bot size={16} color="#06B6D4" />
        <select
          style={{ ...styles.select, fontFamily: "'JetBrains Mono', monospace" }}
          value={serviceName}
          onChange={(e) => setServiceName(e.target.value)}
          disabled={loadingAgents || availableAgents.length === 0}
        >
          {loadingAgents ? (
            <option value={serviceName}>Loading agents...</option>
          ) : availableAgents.length === 0 ? (
            <option value={serviceName}>{serviceName}</option>
          ) : (
            availableAgents.map((a) => (
              <option key={a.serviceName} value={a.serviceName}>
                {a.serviceName}
              </option>
            ))
          )}
        </select>
      </div>

      <TimeRangeSelector filters={filters} onChange={onChange} />

      {/* Errors-only pill toggle */}
      <div
        style={styles.toggleContainer}
        onClick={handleToggle}
        role="switch"
        aria-checked={filters.errorsOnly}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            handleToggle()
          }
        }}
      >
        <div
          style={{
            ...styles.toggleTrack,
            background: filters.errorsOnly ? '#FF5252' : '#334155',
          }}
        >
          <div
            style={{
              ...styles.toggleThumb,
              left: filters.errorsOnly ? '25px' : '3px',
            }}
          />
        </div>
        <span
          style={{
            ...styles.toggleLabel,
            color: filters.errorsOnly ? '#FF5252' : '#78909C',
          }}
        >
          Errors Only
        </span>
      </div>

      {/* Auto-Refresh pill toggle */}
      <div
        style={styles.toggleContainer}
        onClick={() =>
          onAutoRefreshChange({ ...autoRefresh, enabled: !autoRefresh.enabled })
        }
        role="switch"
        aria-checked={autoRefresh.enabled}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onAutoRefreshChange({ ...autoRefresh, enabled: !autoRefresh.enabled })
          }
        }}
      >
        <div
          style={{
            ...styles.toggleTrack,
            background: autoRefresh.enabled ? '#06B6D4' : '#334155',
          }}
        >
          <div
            style={{
              ...styles.toggleThumb,
              left: autoRefresh.enabled ? '25px' : '3px',
            }}
          />
        </div>
        <span
          style={{
            ...styles.toggleLabel,
            color: autoRefresh.enabled ? '#06B6D4' : '#78909C',
          }}
        >
          Auto-Refresh
        </span>
      </div>

      {autoRefresh.enabled && (
        <>
          <select
            style={styles.select}
            value={autoRefresh.intervalSeconds}
            onChange={(e) =>
              onAutoRefreshChange({
                ...autoRefresh,
                intervalSeconds: Number(e.target.value) as RefreshInterval,
              })
            }
          >
            <option value={30}>30s</option>
            <option value={60}>1m</option>
            <option value={300}>5m</option>
          </select>
          {lastUpdated && (
            <span style={{ fontSize: '12px', color: '#78909C' }}>
              Updated {formatTime(lastUpdated)}
            </span>
          )}
        </>
      )}

      <button
        style={canLoad ? styles.loadButton : styles.loadButtonDisabled}
        onClick={onLoad}
        disabled={!canLoad}
      >
        {loading ? 'Loading...' : 'Load'}
      </button>
    </div>
  )
}
