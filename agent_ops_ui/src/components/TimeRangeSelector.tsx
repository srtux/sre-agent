import { useState, useRef, useEffect } from 'react'
import { Clock, ChevronDown, Check, Calendar } from 'lucide-react'
import type { GraphFilters } from '../types'

export interface TimeRangePreset {
  label: string
  hours: number
}

const SECTIONS = [
  {
    label: 'QUICK',
    presets: [
      { label: 'Last 5 minutes', hours: 5 / 60 },
      { label: 'Last 15 minutes', hours: 15 / 60 },
      { label: 'Last 30 minutes', hours: 30 / 60 },
    ],
  },
  {
    label: 'HOURS',
    presets: [
      { label: 'Last 1 hour', hours: 1 },
      { label: 'Last 3 hours', hours: 3 },
      { label: 'Last 6 hours', hours: 6 },
      { label: 'Last 12 hours', hours: 12 },
    ],
  },
  {
    label: 'DAYS',
    presets: [
      { label: 'Last 1 day', hours: 24 },
      { label: 'Last 2 days', hours: 48 },
      { label: 'Last 7 days', hours: 168 },
      { label: 'Last 14 days', hours: 336 },
      { label: 'Last 30 days', hours: 720 },
    ],
  },
]

interface TimeRangeSelectorProps {
  filters: GraphFilters
  onChange: (filters: GraphFilters) => void
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    zIndex: 1,
  },
  trigger: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    height: '32px',
    padding: '0 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    color: '#F0F4F8',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer',
    outline: 'none',
    userSelect: 'none',
    transition: 'background 0.2s',
  },
  dropdown: {
    position: 'absolute',
    top: 'calc(100% + 4px)',
    left: 0,
    width: '240px',
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '12px',
    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
    zIndex: 500000,
    padding: '8px 0',
    maxHeight: '400px',
    overflowY: 'auto',
  },
  sectionHeader: {
    fontSize: '9px',
    fontWeight: 700,
    color: '#78909C',
    letterSpacing: '1.2px',
    padding: '8px 16px 4px',
  },
  itemRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    cursor: 'pointer',
    fontSize: '12px',
    transition: 'background 0.15s',
  },
  itemActive: {
    color: '#06B6D4',
    background: 'rgba(6, 182, 212, 0.1)',
  },
  itemInactive: {
    color: '#F0F4F8',
  },
  divider: {
    height: '1px',
    background: 'rgba(255, 255, 255, 0.1)',
    margin: '4px 0',
  },
  customRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    cursor: 'pointer',
    fontSize: '12px',
    color: '#F0F4F8',
    transition: 'background 0.15s',
  },
}

export default function TimeRangeSelector({ filters, onChange }: TimeRangeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Find active label
  const allPresets = SECTIONS.flatMap((s) => s.presets)
  // use Math.abs to match floating point approx
  const activePreset = allPresets.find((p) => Math.abs(p.hours - filters.hours) < 0.001)
  const displayLabel = activePreset ? activePreset.label : 'Custom range'

  return (
    <div style={styles.container} ref={containerRef}>
      <button
        style={styles.trigger}
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)')}
      >
        <Clock size={14} color="#78909C" />
        {displayLabel}
        <ChevronDown size={14} color="#78909C" />
      </button>

      {isOpen && (
        <div style={styles.dropdown}>
          {SECTIONS.map((section) => (
            <div key={section.label}>
              <div style={styles.sectionHeader}>{section.label}</div>
              {section.presets.map((preset) => {
                const isActive = Math.abs(preset.hours - filters.hours) < 0.001
                return (
                  <div
                    key={preset.label}
                    style={{
                      ...styles.itemRow,
                      ...(isActive ? styles.itemActive : styles.itemInactive),
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) e.currentTarget.style.background = 'transparent'
                    }}
                    onClick={() => {
                      onChange({ ...filters, hours: preset.hours, startTime: undefined, endTime: undefined })
                      setIsOpen(false)
                    }}
                  >
                    <span style={{ flex: 1, fontWeight: isActive ? 600 : 400 }}>{preset.label}</span>
                    {isActive && <Check size={14} color="#06B6D4" />}
                  </div>
                )
              })}
              <div style={styles.divider} />
            </div>
          ))}

          <div style={styles.sectionHeader}>CUSTOM</div>
          <div
            style={styles.customRow}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            onClick={() => {
              // Not implementing complete date picker for custom right now
              setIsOpen(false)
            }}
          >
            <Calendar size={14} color="#78909C" />
            <span style={{ flex: 1 }}>Custom range...</span>
          </div>
        </div>
      )}
    </div>
  )
}
