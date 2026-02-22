import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react'

// --- Types ---

export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d'

export interface DashboardFilters {
  timeRange: TimeRange
  /** Empty array means "All agents" */
  selectedAgents: string[]
  groupByAgent: boolean
}

interface DashboardFilterActions {
  setTimeRange: (range: TimeRange) => void
  setSelectedAgents: (agents: string[]) => void
  toggleAgent: (agentId: string) => void
  setGroupByAgent: (enabled: boolean) => void
  resetFilters: () => void
}

export type DashboardFilterContextValue = DashboardFilters & DashboardFilterActions

// --- Defaults ---

const DEFAULT_FILTERS: DashboardFilters = {
  timeRange: '24h',
  selectedAgents: [],
  groupByAgent: false,
}

// --- Context ---

const DashboardFilterContext = createContext<DashboardFilterContextValue | undefined>(undefined)

// --- Provider ---

export function DashboardFilterProvider({
  children,
  initialFilters,
}: {
  children: ReactNode
  initialFilters?: Partial<DashboardFilters>
}) {
  const [timeRange, setTimeRange] = useState<TimeRange>(
    initialFilters?.timeRange ?? DEFAULT_FILTERS.timeRange,
  )
  const [selectedAgents, setSelectedAgents] = useState<string[]>(
    initialFilters?.selectedAgents ?? DEFAULT_FILTERS.selectedAgents,
  )
  const [groupByAgent, setGroupByAgent] = useState<boolean>(
    initialFilters?.groupByAgent ?? DEFAULT_FILTERS.groupByAgent,
  )

  const toggleAgent = useCallback((agentId: string) => {
    setSelectedAgents((prev) =>
      prev.includes(agentId)
        ? prev.filter((id) => id !== agentId)
        : [...prev, agentId],
    )
  }, [])

  const resetFilters = useCallback(() => {
    setTimeRange(DEFAULT_FILTERS.timeRange)
    setSelectedAgents(DEFAULT_FILTERS.selectedAgents)
    setGroupByAgent(DEFAULT_FILTERS.groupByAgent)
  }, [])

  const value: DashboardFilterContextValue = {
    timeRange,
    selectedAgents,
    groupByAgent,
    setTimeRange,
    setSelectedAgents,
    toggleAgent,
    setGroupByAgent,
    resetFilters,
  }

  return (
    <DashboardFilterContext.Provider value={value}>
      {children}
    </DashboardFilterContext.Provider>
  )
}

// --- Hook ---

// eslint-disable-next-line react-refresh/only-export-components
export function useDashboardFilters(): DashboardFilterContextValue {
  const context = useContext(DashboardFilterContext)
  if (context === undefined) {
    throw new Error('useDashboardFilters must be used within a <DashboardFilterProvider>')
  }
  return context
}
