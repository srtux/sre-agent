import { useState, useEffect, useRef } from 'react'
import type { GraphFilters, AutoRefreshConfig, RefreshInterval, Tab } from '../types'
import { Bot, ChevronDown, Check, LayoutGrid, List } from 'lucide-react'
import TimeRangeSelector from './TimeRangeSelector'
import { useAgentContext } from '../contexts/AgentContext'
import { useDashboardFilters } from '../contexts/DashboardFilterContext'

interface GraphToolbarProps {
  filters: GraphFilters
  onChange: (filters: GraphFilters) => void
  onLoad: () => void
  loading: boolean
  autoRefresh: AutoRefreshConfig
  onAutoRefreshChange: (config: AutoRefreshConfig) => void
  lastUpdated: Date | null
  activeTab: Tab
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '8px 24px',
    background: 'rgba(30, 41, 59, 0.4)',
    backdropFilter: 'blur(10px)',
    flexWrap: 'nowrap',
    borderRadius: '16px',
    margin: '16px 24px',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    position: 'relative',
    zIndex: 100,
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
  multiSelectTrigger: {
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '6px',
    color: '#F0F4F8',
    fontSize: '14px',
    padding: '6px 12px',
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
    padding: '0 12px',
    fontSize: '13px',
    color: '#F0F4F8',
    cursor: 'pointer',
    transition: 'background 0.1s',
  },
  dropdownItemHover: {
    background: 'rgba(6, 182, 212, 0.1)',
  },
  viewToggle: {
    display: 'flex',
    background: 'rgba(15, 23, 42, 0.4)',
    borderRadius: '10px',
    padding: '4px',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    marginLeft: 'auto',
  },
  viewToggleButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '6px 14px',
    borderRadius: '8px',
    border: 'none',
    background: 'transparent',
    color: '#64748B',
    cursor: 'pointer',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
  },
  viewToggleButtonActive: {
    background: '#38BDF8',
    color: '#0F172A',
  },
  checkBox: {
    width: '18px',
    height: '18px',
    borderRadius: '4px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    transition: 'border-color 0.2s',
  },
  checkBoxChecked: {
    width: '18px',
    height: '18px',
    borderRadius: '4px',
    border: '1px solid #38BDF8',
    background: '#38BDF8',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
}
function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

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
        onClick={() => setOpen((v: boolean) => !v)}
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
            <div style={{ padding: '16px', fontSize: '13px', color: '#78909C' }}>Loading agents...</div>
          ) : availableAgents.length === 0 ? (
            <div style={{ padding: '16px', fontSize: '13px', color: '#78909C' }}>No agents found</div>
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

export default function GraphToolbar({
  filters,
  onChange,
  onLoad,
  loading,
  autoRefresh,
  onAutoRefreshChange,
  lastUpdated,
  activeTab,
}: GraphToolbarProps) {
  const { serviceName, setServiceName, availableAgents, loadingAgents, registryViewMode, setRegistryViewMode } = useAgentContext()
  const { selectedAgents, toggleAgent, groupByAgent, setGroupByAgent } = useDashboardFilters()

  const canLoad = !loading && filters.projectId.trim().length > 0
  const agentNames = availableAgents.map(a => a.serviceName)

  const handleToggle = () => {
    onChange({ ...filters, errorsOnly: !filters.errorsOnly })
  }

  return (
    <div style={styles.bar}>
      {/* Agent Selector / Multi-select */}
      {activeTab !== 'agents' && activeTab !== 'tools' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Bot size={16} color="#06B6D4" />

          {activeTab === 'dashboard' ? (
            <AgentMultiSelect
              availableAgents={agentNames}
              selectedAgents={selectedAgents}
              onToggle={toggleAgent}
              loading={loadingAgents}
            />
          ) : (
              <select
                style={{ ...styles.select, fontFamily: "'JetBrains Mono', monospace" }}
                value={serviceName}
                onChange={(e) => setServiceName(e.target.value)}
                disabled={loadingAgents}
              >
                {activeTab !== 'topology' && activeTab !== 'trajectory' && (
                  <option value="">All Agents</option>
                )}
                {loadingAgents ? (
                  <option disabled value={serviceName}>Loading agents...</option>
                ) : availableAgents.length === 0 ? (
                    <option disabled value={serviceName}>No agents available</option>
                ) : (
                  availableAgents.map((a) => (
                    <option key={a.serviceName} value={a.serviceName}>
                      {a.serviceName}
                    </option>
                  ))
                )}
              </select>
          )}
        </div>
      )}

      {/* Group by Agent Toggle (Dashboard Only) */}
      {activeTab === 'dashboard' && (
        <div
          style={styles.toggleContainer}
          onClick={() => setGroupByAgent(!groupByAgent)}
          role="switch"
          aria-checked={groupByAgent}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              setGroupByAgent(!groupByAgent)
            }
          }}
        >
          <div
            style={{
              ...styles.toggleTrack,
              background: groupByAgent ? '#06B6D4' : '#334155',
            }}
          >
            <div
              style={{
                ...styles.toggleThumb,
                left: groupByAgent ? '25px' : '3px',
              }}
            />
          </div>
          <span
            style={{
              ...styles.toggleLabel,
              color: groupByAgent ? '#06B6D4' : '#78909C',
            }}
          >
            Group by Agent
          </span>
        </div>
      )}

      <TimeRangeSelector filters={filters} onChange={onChange} />

      {/* Severity filter pills (Logs tab only) */}
      {activeTab === 'logs' && (() => {
        const severities = ['INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const
        const sevColors: Record<string, { bg: string; border: string; text: string }> = {
          INFO: { bg: 'rgba(56, 189, 248, 0.15)', border: 'rgba(56, 189, 248, 0.4)', text: '#38BDF8' },
          WARNING: { bg: 'rgba(250, 204, 21, 0.15)', border: 'rgba(250, 204, 21, 0.4)', text: '#FACC15' },
          ERROR: { bg: 'rgba(248, 113, 113, 0.15)', border: 'rgba(248, 113, 113, 0.4)', text: '#F87171' },
          CRITICAL: { bg: 'rgba(168, 85, 247, 0.15)', border: 'rgba(168, 85, 247, 0.4)', text: '#A855F7' },
        }
        const current = filters.logSeverity || []
        const toggle = (sev: string) => {
          const next = current.includes(sev)
            ? current.filter((s) => s !== sev)
            : [...current, sev]
          onChange({ ...filters, logSeverity: next })
        }
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {severities.map((sev) => {
              const isActive = current.includes(sev)
              const c = sevColors[sev]
              return (
                <button
                  key={sev}
                  onClick={() => toggle(sev)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '12px',
                    border: `1px solid ${isActive ? c.border : 'rgba(255,255,255,0.1)'}`,
                    background: isActive ? c.bg : 'transparent',
                    color: isActive ? c.text : '#78909C',
                    fontSize: '12px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                    fontFamily: "'Outfit', sans-serif",
                  }}
                >
                  {sev}
                </button>
              )
            })}
          </div>
        )
      })()}

      {(activeTab === 'topology' || activeTab === 'trajectory') && (
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
      )}

      {(activeTab === 'dashboard' || activeTab === 'topology' || activeTab === 'trajectory') && (
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
      )}
      {(activeTab === 'dashboard' || activeTab === 'topology' || activeTab === 'trajectory') && autoRefresh.enabled && (
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

      {(activeTab === 'agents' || activeTab === 'tools') && (
        <div style={styles.viewToggle}>
          <button
            onClick={() => setRegistryViewMode('card')}
            style={{
              ...styles.viewToggleButton,
              ...(registryViewMode === 'card' ? styles.viewToggleButtonActive : {}),
            }}
            title="Card View"
            aria-label="Card View"
          >
            <LayoutGrid size={16} />
          </button>
          <button
            onClick={() => setRegistryViewMode('table')}
            style={{
              ...styles.viewToggleButton,
              ...(registryViewMode === 'table' ? styles.viewToggleButtonActive : {}),
            }}
            title="Table View"
            aria-label="Table View"
          >
            <List size={16} />
          </button>
        </div>
      )}

      {activeTab !== 'agents' && activeTab !== 'tools' && (
        <button
          style={canLoad ? styles.loadButton : styles.loadButtonDisabled}
          onClick={onLoad}
          disabled={!canLoad}
        >
          {loading ? 'Loading...' : 'Load'}
        </button>
      )}
    </div>
  )
}
