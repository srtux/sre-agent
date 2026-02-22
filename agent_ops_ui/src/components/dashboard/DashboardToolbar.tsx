import { useCallback, useState, useRef, useEffect } from 'react'
import { Clock, Users, LayoutGrid, RotateCcw, ChevronDown, Check } from 'lucide-react'
import { useDashboardFilters, type TimeRange } from '../../contexts/DashboardFilterContext'

// --- Constants ---

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: '1h', label: 'Last 1 hour' },
  { value: '6h', label: 'Last 6 hours' },
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
]

// --- Styles ---

const styles: Record<string, React.CSSProperties> = {
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '10px 24px',
    background: '#1E293B',
    borderBottom: '1px solid #334155',
    flexWrap: 'wrap',
  },
  group: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    position: 'relative',
  },
  label: {
    fontSize: '12px',
    fontWeight: 500,
    color: '#78909C',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  select: {
    background: '#0F172A',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#F0F4F8',
    fontSize: '13px',
    padding: '6px 30px 6px 10px',
    cursor: 'pointer',
    appearance: 'none' as const,
    minWidth: '140px',
  },
  selectWrapper: {
    position: 'relative' as const,
    display: 'inline-flex',
    alignItems: 'center',
  },
  selectChevron: {
    position: 'absolute' as const,
    right: '8px',
    pointerEvents: 'none' as const,
    color: '#78909C',
  },
  multiSelectTrigger: {
    background: '#0F172A',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#F0F4F8',
    fontSize: '13px',
    padding: '6px 30px 6px 10px',
    cursor: 'pointer',
    minWidth: '160px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    textAlign: 'left' as const,
  },
  dropdown: {
    position: 'absolute' as const,
    top: '100%',
    left: '0',
    marginTop: '4px',
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '6px',
    minWidth: '200px',
    maxHeight: '240px',
    overflowY: 'auto' as const,
    zIndex: 50,
    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
  },
  dropdownItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    fontSize: '13px',
    color: '#F0F4F8',
    cursor: 'pointer',
    transition: 'background 0.1s',
  },
  dropdownItemHover: {
    background: 'rgba(6, 182, 212, 0.1)',
  },
  checkBox: {
    width: '16px',
    height: '16px',
    borderRadius: '3px',
    border: '1px solid #475569',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  checkBoxChecked: {
    width: '16px',
    height: '16px',
    borderRadius: '3px',
    border: '1px solid #06B6D4',
    background: '#06B6D4',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  toggle: {
    width: '36px',
    height: '20px',
    borderRadius: '10px',
    background: '#334155',
    cursor: 'pointer',
    position: 'relative' as const,
    transition: 'background 0.2s',
    border: 'none',
    padding: 0,
    flexShrink: 0,
  },
  toggleActive: {
    width: '36px',
    height: '20px',
    borderRadius: '10px',
    background: '#06B6D4',
    cursor: 'pointer',
    position: 'relative' as const,
    transition: 'background 0.2s',
    border: 'none',
    padding: 0,
    flexShrink: 0,
  },
  toggleKnob: {
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    background: '#F0F4F8',
    position: 'absolute' as const,
    top: '2px',
    left: '2px',
    transition: 'transform 0.2s',
  },
  toggleKnobActive: {
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    background: '#F0F4F8',
    position: 'absolute' as const,
    top: '2px',
    left: '2px',
    transition: 'transform 0.2s',
    transform: 'translateX(16px)',
  },
  resetBtn: {
    background: 'transparent',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#78909C',
    fontSize: '12px',
    padding: '6px 10px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    marginLeft: 'auto',
    transition: 'color 0.15s, border-color 0.15s',
  },
  emptyState: {
    padding: '16px 12px',
    fontSize: '13px',
    color: '#78909C',
    textAlign: 'center' as const,
  },
}

// --- Agent multi-select dropdown ---

interface AgentMultiSelectProps {
  availableAgents: string[]
  selectedAgents: string[]
  onToggle: (agentId: string) => void
  loading?: boolean
}

function AgentMultiSelect({ availableAgents, selectedAgents, onToggle, loading }: AgentMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const displayLabel =
    selectedAgents.length === 0
      ? 'All Agents'
      : selectedAgents.length === 1
        ? selectedAgents[0]
        : `${selectedAgents.length} agents`

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        style={styles.multiSelectTrigger}
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {displayLabel}
        </span>
        <ChevronDown size={14} style={{ color: '#78909C', flexShrink: 0 }} />
      </button>

      {open && (
        <div style={styles.dropdown}>
          {loading ? (
            <div style={styles.emptyState}>Loading agents...</div>
          ) : availableAgents.length === 0 ? (
            <div style={styles.emptyState}>No agents found</div>
          ) : (
            availableAgents.map((agent, idx) => {
              const isChecked = selectedAgents.includes(agent)
              return (
                <div
                  key={agent}
                  style={{
                    ...styles.dropdownItem,
                    ...(hoveredIdx === idx ? styles.dropdownItemHover : {}),
                  }}
                  onMouseEnter={() => setHoveredIdx(idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  onClick={() => onToggle(agent)}
                >
                  <div style={isChecked ? styles.checkBoxChecked : styles.checkBox}>
                    {isChecked && <Check size={12} color="#0F172A" />}
                  </div>
                  <span>{agent}</span>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

// --- Main toolbar ---

interface DashboardToolbarProps {
  availableAgents?: string[]
  loadingAgents?: boolean
}

export default function DashboardToolbar({ availableAgents = [], loadingAgents = false }: DashboardToolbarProps) {
  const {
    timeRange,
    selectedAgents,
    groupByAgent,
    setTimeRange,
    toggleAgent,
    setGroupByAgent,
    resetFilters,
  } = useDashboardFilters()

  const handleTimeRangeChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setTimeRange(e.target.value as TimeRange)
    },
    [setTimeRange],
  )

  return (
    <div style={styles.toolbar}>
      {/* Time range */}
      <div style={styles.group}>
        <span style={styles.label}>
          <Clock size={13} />
          Range
        </span>
        <div style={styles.selectWrapper}>
          <select
            style={styles.select}
            value={timeRange}
            onChange={handleTimeRangeChange}
          >
            {TIME_RANGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown size={14} style={styles.selectChevron} />
        </div>
      </div>

      {/* Agent multi-select */}
      <div style={styles.group}>
        <span style={styles.label}>
          <Users size={13} />
          Agents
        </span>
        <AgentMultiSelect
          availableAgents={availableAgents}
          selectedAgents={selectedAgents}
          onToggle={toggleAgent}
          loading={loadingAgents}
        />
      </div>

      {/* Group by agent toggle */}
      <div style={styles.group}>
        <span style={styles.label}>
          <LayoutGrid size={13} />
          Group by Agent
        </span>
        <button
          type="button"
          style={groupByAgent ? styles.toggleActive : styles.toggle}
          onClick={() => setGroupByAgent(!groupByAgent)}
          aria-pressed={groupByAgent}
          aria-label="Group by agent"
        >
          <div style={groupByAgent ? styles.toggleKnobActive : styles.toggleKnob} />
        </button>
      </div>

      {/* Reset */}
      <button
        type="button"
        style={styles.resetBtn}
        onClick={resetFilters}
      >
        <RotateCcw size={12} />
        Reset
      </button>
    </div>
  )
}
