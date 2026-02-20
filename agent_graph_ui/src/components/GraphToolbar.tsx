import type { GraphFilters, ViewMode, AutoRefreshConfig, RefreshInterval } from '../types'

interface GraphToolbarProps {
  filters: GraphFilters
  onChange: (filters: GraphFilters) => void
  onLoad: () => void
  loading: boolean
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
  autoRefresh: AutoRefreshConfig
  onAutoRefreshChange: (config: AutoRefreshConfig) => void
  lastUpdated: Date | null
}

const hoursOptions = [
  { label: '1h', value: 1 },
  { label: '6h', value: 6 },
  { label: '24h', value: 24 },
  { label: '7d', value: 168 },
]

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 24px',
    borderBottom: '1px solid #21262d',
    background: '#161b22',
    flexWrap: 'wrap',
  },
  label: {
    fontSize: '13px',
    color: '#8b949e',
  },
  input: {
    padding: '6px 12px',
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '6px',
    color: '#c9d1d9',
    fontSize: '14px',
    outline: 'none',
    width: '220px',
  },
  select: {
    padding: '6px 12px',
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '6px',
    color: '#c9d1d9',
    fontSize: '14px',
    outline: 'none',
    cursor: 'pointer',
  },
  loadButton: {
    padding: '6px 16px',
    background: '#238636',
    border: '1px solid #2ea043',
    borderRadius: '6px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  loadButtonDisabled: {
    padding: '6px 16px',
    background: '#21262d',
    border: '1px solid #30363d',
    borderRadius: '6px',
    color: '#484f58',
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
  viewMode,
  onViewModeChange,
  autoRefresh,
  onAutoRefreshChange,
  lastUpdated,
}: GraphToolbarProps) {
  const canLoad = !loading && filters.projectId.trim().length > 0

  const handleToggle = () => {
    onChange({ ...filters, errorsOnly: !filters.errorsOnly })
  }

  return (
    <div style={styles.bar}>
      <span style={styles.label}>Project ID</span>
      <input
        style={styles.input}
        type="text"
        placeholder="my-gcp-project"
        value={filters.projectId}
        onChange={(e) =>
          onChange({ ...filters, projectId: e.target.value })
        }
      />

      <span style={styles.label}>Time Range</span>
      <select
        style={styles.select}
        value={filters.hours}
        onChange={(e) =>
          onChange({ ...filters, hours: Number(e.target.value) })
        }
      >
        {hoursOptions.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* View Mode segmented control */}
      <span style={styles.label}>View</span>
      <div style={{ display: 'flex', gap: '0px' }}>
        {(['topology', 'cost', 'latency'] as ViewMode[]).map((mode, idx) => {
          const isActive = viewMode === mode
          const labels: Record<ViewMode, string> = {
            topology: 'Topology',
            cost: 'Cost Hotspots',
            latency: 'Latency',
          }
          return (
            <button
              key={mode}
              onClick={() => onViewModeChange(mode)}
              style={{
                padding: '6px 14px',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                border: '1px solid #30363d',
                borderLeft: idx === 0 ? '1px solid #30363d' : 'none',
                borderRadius: idx === 0 ? '6px 0 0 6px' : idx === 2 ? '0 6px 6px 0' : '0',
                background: isActive ? '#1f6feb' : '#0d1117',
                color: isActive ? '#ffffff' : '#8b949e',
                transition: 'background 0.15s, color 0.15s',
              }}
            >
              {labels[mode]}
            </button>
          )
        })}
      </div>

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
            background: filters.errorsOnly ? '#f85149' : '#21262d',
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
            color: filters.errorsOnly ? '#f85149' : '#8b949e',
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
            background: autoRefresh.enabled ? '#58a6ff' : '#21262d',
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
            color: autoRefresh.enabled ? '#58a6ff' : '#8b949e',
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
            <span style={{ fontSize: '12px', color: '#8b949e' }}>
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
