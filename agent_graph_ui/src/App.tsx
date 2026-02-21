import { useState, useCallback, useEffect } from 'react'
import axios from 'axios'
import TopologyGraph from './components/TopologyGraph'
import TrajectorySankey from './components/TrajectorySankey'
import SidePanel from './components/SidePanel'
import GraphToolbar from './components/GraphToolbar'
import Onboarding from './components/Onboarding'
import type {
  TopologyResponse,
  SankeyResponse,
  SelectedElement,
  GraphFilters,
  AutoRefreshConfig,
  TimeSeriesData,
} from './types'
import RegistryPage from './components/RegistryPage'

type Tab = 'registry' | 'topology' | 'trajectory'

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
  activeTab: Tab,
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

  if (activeTab && activeTab !== 'registry') {
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

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('registry')
  const [filters, setFilters] = useState<GraphFilters>({
    projectId: localStorage.getItem('agent_graph_project_id') || '',
    hours: 24,
    errorsOnly: false,
    traceDataset: localStorage.getItem('agent_graph_trace_dataset') || 'traces',
    serviceName: localStorage.getItem('agent_graph_service_name') || 'sre-agent',
  })
  const [selected, setSelected] = useState<SelectedElement | null>(null)
  const [topologyData, setTopologyData] = useState<TopologyResponse | null>(null)
  const [sankeyData, setSankeyData] = useState<SankeyResponse | null>(null)
  const [timeseriesData, setTimeseriesData] = useState<TimeSeriesData | null>(null)
  const [loadingTopology, setLoadingTopology] = useState(false)
  const [loadingSankey, setLoadingSankey] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [needsSetup, setNeedsSetup] = useState(false)
  const [settingUp, setSettingUp] = useState(false)
  const [setupError, setSetupError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState<AutoRefreshConfig>({
    enabled: false,
    intervalSeconds: 60,
  })
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  // --- URL deep linking: parse on mount ---
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)

    const urlProjectId = params.get('project_id')
    const urlTimeRange = params.get('time_range')
    const urlNode = params.get('node')
    const urlTraceId = params.get('trace_id')
    const urlTab = params.get('tab')

    let hours = 1
    if (urlTimeRange) {
      const parsed = parseTimeRange(urlTimeRange)
      if (parsed !== null) {
        hours = parsed
      }
    }

    setFilters((prev) => ({
      ...prev,
      projectId: urlProjectId ?? prev.projectId,
      hours,
    }))

    if (urlNode) {
      setSelected({ kind: 'node', id: urlNode })
    }

    if (urlTraceId) {
      setActiveTab('trajectory')
    } else if (urlTab === 'topology' || urlTab === 'trajectory') {
      setActiveTab(urlTab as Tab)
    }
  }, [])

  // --- URL deep linking: sync state back to URL ---
  useEffect(() => {
    const params = buildSearchParams(filters, selected, activeTab)
    const newUrl = `${window.location.pathname}?${params.toString()}`
    window.history.replaceState(null, '', newUrl)
  }, [filters, selected, activeTab])

  const fetchAll = useCallback(async (isSilent: boolean) => {
    if (!filters.projectId.trim()) return

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
      service_name: filters.serviceName,
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
      if (filters.hours >= 2 && activeTab !== 'registry') {
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
  }, [filters, activeTab])

  const handleLoad = useCallback(() => fetchAll(false), [fetchAll])

  // Auto-load on initial project_id
  const [hasAutoLoaded, setHasAutoLoaded] = useState(false)
  useEffect(() => {
    if (filters.projectId && !hasAutoLoaded) {
      setHasAutoLoaded(true)
      fetchAll(false)
    }
  }, [filters.projectId, hasAutoLoaded, fetchAll])

  const handleSetup = async (dataset: string, serviceName: string) => {
    setSettingUp(true)
    setSetupError(null)
    try {
      await axios.post('/api/v1/graph/setup', {
        project_id: filters.projectId,
        trace_dataset: dataset,
        service_name: serviceName
      })
      localStorage.setItem('agent_graph_project_id', filters.projectId)
      localStorage.setItem('agent_graph_trace_dataset', dataset)
      localStorage.setItem('agent_graph_service_name', serviceName)

      setFilters(prev => ({
        ...prev,
        traceDataset: dataset,
        serviceName: serviceName
      }))
      setNeedsSetup(false)
      fetchAll(false)
    } catch (err) {
      const axiosErr = err as import('axios').AxiosError<{ detail?: string }>
      setSetupError(axiosErr?.response?.data?.detail || String(err))
    } finally {
      setSettingUp(false)
    }
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

      <GraphToolbar
        filters={filters}
        onChange={setFilters}
        onLoad={handleLoad}
        loading={isLoading}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        lastUpdated={lastUpdated}
      />

      <div style={styles.tabBar}>
        <button
          style={activeTab === 'registry' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('registry')}
        >
          Registry
        </button>
        <button
          style={activeTab === 'topology' ? styles.tabActive : styles.tab}
          onClick={() => {
            if (activeTab !== 'topology') fetchAll(false)
            setActiveTab('topology')
          }}
        >
          Topology
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
      </div>

      <div style={styles.content}>
        {error && !needsSetup && <div style={styles.error}>{error}</div>}

        {needsSetup ? (
          <Onboarding
            projectId={filters.projectId}
            onSetup={handleSetup}
            loading={settingUp}
            error={setupError}
          />
        ) : (
            <div style={{ display: 'flex', flex: 1, position: 'relative', overflow: 'hidden' }}>
              <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                {activeTab === 'registry' && (
                  <RegistryPage
                    filters={filters}
                    onSelectAgent={(serviceName) => {
                      setFilters(prev => ({ ...prev, serviceName }))
                      localStorage.setItem('agent_graph_service_name', serviceName)
                      setActiveTab('topology')
                      // need to trigger a re-fetch with new serviceName
                      setTimeout(() => fetchAll(false), 0)
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
                      ? 'Loading topology data...'
                      : 'Enter a project ID and click Load to visualize the agent topology.'}
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
          </div>

          <SidePanel
            selected={selected}
            projectId={filters.projectId}
            hours={filters.hours}
                onClose={() => setSelected(null)}
            sparklineData={timeseriesData}
                filters={filters}
          />
        </div>
        )}
      </div>
    </div>
  )
}

export default App
