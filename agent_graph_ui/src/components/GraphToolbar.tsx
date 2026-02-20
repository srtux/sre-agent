import type { GraphFilters } from '../types'

interface GraphToolbarProps {
  filters: GraphFilters
  onChange: (filters: GraphFilters) => void
  onLoad: () => void
  loading: boolean
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

export default function GraphToolbar({
  filters,
  onChange,
  onLoad,
  loading,
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
