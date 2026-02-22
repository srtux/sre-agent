import { useState, useCallback, useEffect } from 'react'
import axios from 'axios'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TopologyGraph from './components/TopologyGraph'
import TrajectorySankey from './components/TrajectorySankey'
import SidePanel from './components/SidePanel'
import GraphToolbar from './components/GraphToolbar'
import Onboarding from './components/Onboarding'
import { AgentProvider, useAgentContext } from './contexts/AgentContext'
import type {
  TopologyResponse,
  SankeyResponse,
  SelectedElement,
  GraphFilters,
  AutoRefreshConfig,
  TimeSeriesData,
} from './types'
import RegistryPage from './components/RegistryPage'
import AgentDashboard from './components/dashboard/AgentDashboard'

type Tab = 'agents' | 'tools' | 'topology' | 'trajectory' | 'dashboard'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

/** Parse a time_range string like "1h", "6h", "24h", "7d" into hours. */
function parseTimeRange(raw: string): number | null {
  const match = raw.match(/^(\d+)(m|h|d)$/)
  if (!match) return null
  const value = parseInt(match[1], 10)
  const unit = match[2]
  if (unit === 'm') return value / 60
  if (unit === 'd') return value * 24
  return value
}

/** Build a URLSearchParams from current app state. */
function buildSearchParams(
  filters: GraphFilters,
  selected: SelectedElement | null,
  activeTab: Tab
): URLSearchParams {
  const params = new URLSearchParams()

  if (filters.projectId) {
    params.set('project_id', filters.projectId)
  }

  // Convert hours back to a human-readable time_range
  if (filters.hours === 168) {
    params.set('time_range', '7d')
  } else if (filters.hours < 1) {
    params.set('time_range', `${Math.round(filters.hours * 60)}m`)
  } else {
    params.set('time_range', `${filters.hours}h`)
  }

  if (selected) {
    if (selected.kind === 'node') {
      params.set('node', selected.id)
    }
  }

  if (activeTab) {
    params.set('tab', activeTab)
  }

  return params
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#0F172A',
    color: '#F0F4F8',
    fontFamily: "'Outfit', sans-serif",

    display: 'flex',
    flexDirection: 'column',
  },
  title: {
    fontSize: '20px',
    fontWeight: 600,
    color: '#F0F4F8',
    marginRight: 'auto',
  },
  tabBar: {
    display: 'flex',
    gap: '0px',
    padding: '0 24px',
    borderBottom: '1px solid #334155',
    background: '#1E293B',
  },
  tab: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    background: 'transparent',
    color: '#78909C',
    borderBottom: '2px solid transparent',
    transition: 'color 0.15s, border-color 0.15s',
  },
  tabActive: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    background: 'transparent',
    color: '#F0F4F8',
    borderBottom: '2px solid #06B6D4',
  },
  content: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    padding: '16px 24px',
  },
  placeholder: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#B0BEC5',
    fontSize: '16px',
  },
  error: {
    padding: '12px 16px',
    background: 'rgba(255, 82, 82, 0.08)',
    border: '1px solid rgba(255, 82, 82, 0.3)',
    borderRadius: '6px',
    color: '#FF5252',
    fontSize: '14px',
    marginBottom: '16px',
  },
}

function AppContent({ activeTab, setActiveTab, filters, setFilters }: {
  activeTab: Tab, setActiveTab: React.Dispatch<React.SetStateAction<Tab>>,
  filters: GraphFilters, setFilters: React.Dispatch<React.SetStateAction<GraphFilters>>
}) {
  const { serviceName, setServiceName } = useAgentContext()
  const [selected, setSelected] = useState<SelectedElement | null>(null)
  const [topologyData, setTopologyData] = useState<TopologyResponse | null>(null)
  const [sankeyData, setSankeyData] = useState<SankeyResponse | null>(null)
  const [timeseriesData, setTimeseriesData] = useState<TimeSeriesData | null>(null)
  const [loadingTopology, setLoadingTopology] = useState(false)
  const [loadingSankey, setLoadingSankey] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [needsSetup, setNeedsSetup] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState<AutoRefreshConfig>({
    enabled: false,
    intervalSeconds: 60,
  })
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  // --- URL deep linking: sync state back to URL ---
  useEffect(() => {
    const params = buildSearchParams(filters, selected, activeTab)
    const newUrl = `${window.location.pathname}?${params.toString()}`
    window.history.replaceState(null, '', newUrl)
  }, [filters, selected, activeTab])

  // --- Initial URL parsing for selected node ---
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlNode = params.get('node')
    if (urlNode) {
      setSelected({ kind: 'node', id: urlNode })
    }
  }, [])

  const fetchAll = useCallback(async (isSilent: boolean) => {
    if (!filters.projectId.trim() || !serviceName.trim()) return

    if (!isSilent) {
      setSelected(null)
      setError(null)
    }
    setLoadingTopology(true)
    setLoadingSankey(true)

    const params = {
      project_id: filters.projectId.trim(),
      hours: filters.hours,
      errors_only: filters.errorsOnly,
      trace_dataset: filters.traceDataset,
      service_name: serviceName.trim(),
    }

    try {
      const fetches: [
        Promise<import('axios').AxiosResponse<TopologyResponse>>,
        Promise<import('axios').AxiosResponse<SankeyResponse>>,
        ...Promise<import('axios').AxiosResponse<TimeSeriesData>>[],
      ] = [
        axios.get<TopologyResponse>('/api/v1/graph/topology', { params }),
        axios.get<SankeyResponse>('/api/v1/graph/trajectories', { params }),
      ]

      // Fetch timeseries when hours >= 2 (endpoint requires ge=2)
      if (filters.hours >= 2 && activeTab !== 'agents' && activeTab !== 'tools') {
        fetches.push(
          axios.get<TimeSeriesData>('/api/v1/graph/timeseries', { params }),
        )
      }

      const results = await Promise.allSettled(fetches)

      const topoRes = results[0]
      const sankeyRes = results[1]
      const tsRes = results.length > 2 ? results[2] : null

      if (topoRes.status === 'fulfilled') {
        setTopologyData(topoRes.value.data)
        setNeedsSetup(false)
      } else if (!isSilent) {
        // Handle setup required
        const err = topoRes.reason as import('axios').AxiosError<{ code?: string, detail?: string }>
        const code = err?.response?.data?.code
        const detail = err?.response?.data?.detail

        if (code === 'NOT_SETUP') {
          setNeedsSetup(true)
        } else {
          setError(`Topology fetch failed: ${detail || err.message || String(err)}`)
        }
      }

      if (sankeyRes.status === 'fulfilled') {
        setSankeyData(sankeyRes.value.data)
      } else if (!isSilent) {
        setError((prev) =>
          prev
            ? `${prev} | Trajectory fetch failed: ${sankeyRes.reason}`
            : `Trajectory fetch failed: ${sankeyRes.reason}`,
        )
      }

      if (tsRes && tsRes.status === 'fulfilled') {
        setTimeseriesData(tsRes.value.data)
      } else {
        setTimeseriesData(null)
      }

      setLastUpdated(new Date())
    } catch (err) {
      if (!isSilent) {
        setError(`Unexpected error: ${err}`)
      }
    } finally {
      setLoadingTopology(false)
      setLoadingSankey(false)
    }
  }, [filters, activeTab, serviceName])

  const handleLoad = useCallback(() => fetchAll(false), [fetchAll])

  // Auto-load on initial project_id and serviceName change
  const [hasAutoLoaded, setHasAutoLoaded] = useState(false)
  useEffect(() => {
    if (filters.projectId && serviceName && !hasAutoLoaded) {
      setHasAutoLoaded(true)
    }
    if (filters.projectId && serviceName) {
      fetchAll(false)
    }
  }, [filters.projectId, serviceName, fetchAll, hasAutoLoaded])

  const handleSetupDone = async (dataset: string, setupServiceName: string) => {
    localStorage.setItem('agent_graph_project_id', filters.projectId)
    localStorage.setItem('agent_graph_trace_dataset', dataset)
    localStorage.setItem('agent_graph_service_name', setupServiceName)

    setFilters(prev => ({
      ...prev,
      traceDataset: dataset,
    }))
    setServiceName(setupServiceName)
    setNeedsSetup(false)
    // fetchAll is triggered by serviceName dependency effect
  }

  // Auto-refresh timer
  useEffect(() => {
    if (!autoRefresh.enabled || lastUpdated === null) return
    const id = setInterval(() => fetchAll(true), autoRefresh.intervalSeconds * 1000)
    return () => clearInterval(id)
  }, [autoRefresh.enabled, autoRefresh.intervalSeconds, lastUpdated, fetchAll])

  const isLoading = loadingTopology || loadingSankey

  return (
    <div style={styles.container}>

      <div style={styles.tabBar}>
        <button
          style={activeTab === 'agents' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('agents')}
        >
          Agents
        </button>
        <button
          style={activeTab === 'tools' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('tools')}
        >
          Tools
        </button>
        <button
          style={activeTab === 'topology' ? styles.tabActive : styles.tab}
          onClick={() => {
            if (activeTab !== 'topology') fetchAll(false)
            setActiveTab('topology')
          }}
        >
          Agent Graph
        </button>
        <button
          style={activeTab === 'trajectory' ? styles.tabActive : styles.tab}
          onClick={() => {
            if (activeTab !== 'trajectory') fetchAll(false)
            setActiveTab('trajectory')
          }}
        >
          Trajectory Flow
        </button>
        <button
          style={activeTab === 'dashboard' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('dashboard')}
        >
          Dashboard
        </button>
      </div>

      {activeTab !== 'dashboard' && (
        <GraphToolbar
          filters={{ ...filters, serviceName }}
          onChange={setFilters}
          onLoad={handleLoad}
          loading={isLoading}
          autoRefresh={autoRefresh}
          onAutoRefreshChange={setAutoRefresh}
          lastUpdated={lastUpdated}
        />
      )}

      <div style={styles.content}>
        {error && !needsSetup && <div style={styles.error}>{error}</div>}

        {needsSetup ? (
          <Onboarding
            projectId={filters.projectId}
            onSetup={handleSetupDone}
            loading={loadingTopology}
            error={error}
          />
        ) : (
            <div style={{ display: 'flex', flex: 1, position: 'relative', overflow: 'hidden' }}>
              <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                {activeTab === 'agents' && (
                  <RegistryPage
                    filters={{ ...filters, serviceName }}
                    mode="agents"
                    onSelectAgent={(name) => {
                      setServiceName(name)
                      setActiveTab('topology')
                    }}
                  />
                )}

                {activeTab === 'tools' && (
                  <RegistryPage
                    filters={{ ...filters, serviceName }}
                    mode="tools"
                    onSelectAgent={(name) => {
                      setServiceName(name)
                      setActiveTab('topology')
                    }}
                  />
                )}

            {activeTab === 'topology' && (
              <>
                {topologyData ? (
                  <TopologyGraph
                    nodes={topologyData.nodes}
                        edges={topologyData.edges}
                    sparklineData={timeseriesData}
                    selectedNodeId={selected?.kind === 'node' ? selected.id : null}
                    onNodeClick={(nodeId) =>
                      setSelected({ kind: 'node', id: nodeId })
                    }
                    onEdgeClick={(sourceId, targetId) =>
                      setSelected({ kind: 'edge', sourceId, targetId })
                    }
                  />
                ) : (
                  <div style={styles.placeholder}>
                    {loadingTopology
                            ? 'Loading agent graph data...'
                            : 'Enter a project ID and click Load to visualize the agent graph.'}
                  </div>
                )}
              </>
            )}

            {activeTab === 'trajectory' && (
              <>
                {sankeyData ? (
                      <TrajectorySankey
                        data={sankeyData}
                        onNodeClick={(nodeId) => setSelected({ kind: 'node', id: nodeId })}
                        onEdgeClick={(sourceId, targetId) => setSelected({ kind: 'edge', sourceId, targetId })}
                      />
                ) : (
                  <div style={styles.placeholder}>
                    {loadingSankey
                      ? 'Loading trajectory data...'
                      : 'Enter a project ID and click Load to visualize agent trajectories.'}
                  </div>
                )}
              </>
            )}

            {activeTab === 'dashboard' && (
              <AgentDashboard />
            )}
          </div>

          <SidePanel
            selected={selected}
            projectId={filters.projectId}
            hours={filters.hours}
                onClose={() => setSelected(null)}
            sparklineData={timeseriesData}
                filters={{ ...filters, serviceName }}
          />
        </div>
        )}
      </div>
    </div>
  )
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>(() => {
    const params = new URLSearchParams(window.location.search)
    const urlTraceId = params.get('trace_id')
    const urlTab = params.get('tab')

    if (urlTraceId) return 'trajectory'
    if (urlTab === 'topology' || urlTab === 'trajectory' || urlTab === 'agents' || urlTab === 'tools' || urlTab === 'dashboard') {
      return urlTab as Tab
    }
    return 'agents'
  })

  const [filters, setFilters] = useState<GraphFilters>(() => {
    const params = new URLSearchParams(window.location.search)
    console.log('[AgentOps DEBUG] App.tsx initialized! search string:', window.location.search)

    const urlProjectId = params.get('project_id')
    console.log('[AgentOps DEBUG] Extracted urlProjectId during init:', urlProjectId)
    const urlTimeRange = params.get('time_range')

    let hours: number = 24
    if (urlTimeRange) {
      const parsed = parseTimeRange(urlTimeRange)
      if (parsed !== null) {
        hours = parsed
      }
    }

    return {
      projectId: urlProjectId || localStorage.getItem('agent_graph_project_id') || '',
      hours: hours,
      errorsOnly: false,
      traceDataset: localStorage.getItem('agent_graph_trace_dataset') || 'traces',
    }
  })

  return (
    <QueryClientProvider client={queryClient}>
      <AgentProvider projectId={filters.projectId}>
        <AppContent
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          filters={filters}
          setFilters={setFilters}
        />
      </AgentProvider>
    </QueryClientProvider>
  )
}

export default App
