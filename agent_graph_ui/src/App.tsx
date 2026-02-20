import { useState, useCallback, useEffect } from 'react'
import axios from 'axios'
import TopologyGraph from './components/TopologyGraph'
import TrajectorySankey from './components/TrajectorySankey'
import SidePanel from './components/SidePanel'
import GraphToolbar from './components/GraphToolbar'
import type {
  TopologyResponse,
  SankeyResponse,
  SelectedElement,
  GraphFilters,
  ViewMode,
  AutoRefreshConfig,
  TimeSeriesData,
} from './types'

type Tab = 'topology' | 'trajectory'

/** Parse a time_range string like "1h", "6h", "24h", "7d" into hours. */
function parseTimeRange(raw: string): number | null {
  const match = raw.match(/^(\d+)(h|d)$/)
  if (!match) return null
  const value = parseInt(match[1], 10)
  const unit = match[2]
  return unit === 'd' ? value * 24 : value
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
  } else {
    params.set('time_range', `${filters.hours}h`)
  }

  if (selected) {
    if (selected.kind === 'node') {
      params.set('node', selected.id)
    }
  }

  if (activeTab === 'trajectory') {
    // Only set tab param when not on the default
    params.set('tab', 'trajectory')
  }

  return params
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#0d1117',
    color: '#c9d1d9',
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif",
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    padding: '16px 24px',
    borderBottom: '1px solid #21262d',
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    flexWrap: 'wrap',
  },
  title: {
    fontSize: '20px',
    fontWeight: 600,
    color: '#e6edf3',
    marginRight: 'auto',
  },
  tabBar: {
    display: 'flex',
    gap: '0px',
    padding: '0 24px',
    borderBottom: '1px solid #21262d',
    background: '#161b22',
  },
  tab: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    background: 'transparent',
    color: '#8b949e',
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
    color: '#e6edf3',
    borderBottom: '2px solid #58a6ff',
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
    color: '#484f58',
    fontSize: '16px',
  },
  error: {
    padding: '12px 16px',
    background: '#3d1a1a',
    border: '1px solid #f85149',
    borderRadius: '6px',
    color: '#f85149',
    fontSize: '14px',
    marginBottom: '16px',
  },
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('topology')
  const [filters, setFilters] = useState<GraphFilters>({
    projectId: '',
    hours: 24,
    errorsOnly: false,
  })
  const [viewMode, setViewMode] = useState<ViewMode>('topology')
  const [selected, setSelected] = useState<SelectedElement | null>(null)
  const [topologyData, setTopologyData] = useState<TopologyResponse | null>(null)
  const [sankeyData, setSankeyData] = useState<SankeyResponse | null>(null)
  const [timeseriesData, setTimeseriesData] = useState<TimeSeriesData | null>(null)
  const [loadingTopology, setLoadingTopology] = useState(false)
  const [loadingSankey, setLoadingSankey] = useState(false)
  const [error, setError] = useState<string | null>(null)
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

    if (urlTraceId || urlTab === 'trajectory') {
      setActiveTab('trajectory')
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
      if (filters.hours >= 2) {
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
      } else if (!isSilent) {
        setError(`Topology fetch failed: ${topoRes.reason}`)
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
  }, [filters])

  const handleLoad = useCallback(() => fetchAll(false), [fetchAll])

  // Auto-refresh timer
  useEffect(() => {
    if (!autoRefresh.enabled || lastUpdated === null) return
    const id = setInterval(() => fetchAll(true), autoRefresh.intervalSeconds * 1000)
    return () => clearInterval(id)
  }, [autoRefresh.enabled, autoRefresh.intervalSeconds, lastUpdated, fetchAll])

  const isLoading = loadingTopology || loadingSankey

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Agent Graph Dashboard</span>
      </div>

      <GraphToolbar
        filters={filters}
        onChange={setFilters}
        onLoad={handleLoad}
        loading={isLoading}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        lastUpdated={lastUpdated}
      />

      <div style={styles.tabBar}>
        <button
          style={activeTab === 'topology' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('topology')}
        >
          Topology
        </button>
        <button
          style={activeTab === 'trajectory' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('trajectory')}
        >
          Trajectory Flow
        </button>
      </div>

      <div style={styles.content}>
        {error && <div style={styles.error}>{error}</div>}

        <div style={{ display: 'flex', flex: 1, position: 'relative', overflow: 'hidden' }}>
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {activeTab === 'topology' && (
              <>
                {topologyData ? (
                  <TopologyGraph
                    nodes={topologyData.nodes}
                    edges={topologyData.edges}
                    viewMode={viewMode}
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
                  <TrajectorySankey data={sankeyData} />
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
            viewMode={viewMode}
            sparklineData={timeseriesData}
          />
        </div>
      </div>
    </div>
  )
}

export default App
