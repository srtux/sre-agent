import { useState, useCallback } from 'react'
import axios from 'axios'
import TopologyGraph from './components/TopologyGraph'
import TrajectorySankey from './components/TrajectorySankey'
import type { TopologyResponse, SankeyResponse } from './types'

type Tab = 'topology' | 'trajectory'

const hoursOptions = [
  { label: '1h', value: 1 },
  { label: '6h', value: 6 },
  { label: '24h', value: 24 },
  { label: '7d', value: 168 },
]

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
  controlsBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 24px',
    borderBottom: '1px solid #21262d',
    background: '#161b22',
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
    padding: '16px 24px',
    display: 'flex',
    flexDirection: 'column',
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
  const [projectId, setProjectId] = useState('')
  const [hours, setHours] = useState(1)
  const [topologyData, setTopologyData] = useState<TopologyResponse | null>(null)
  const [sankeyData, setSankeyData] = useState<SankeyResponse | null>(null)
  const [loadingTopology, setLoadingTopology] = useState(false)
  const [loadingSankey, setLoadingSankey] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleLoad = useCallback(async () => {
    if (!projectId.trim()) return

    setError(null)
    setLoadingTopology(true)
    setLoadingSankey(true)

    const params = { project_id: projectId.trim(), hours }

    try {
      const [topoRes, sankeyRes] = await Promise.allSettled([
        axios.get<TopologyResponse>('/api/v1/graph/topology', { params }),
        axios.get<SankeyResponse>('/api/v1/graph/trajectories', { params }),
      ])

      if (topoRes.status === 'fulfilled') {
        setTopologyData(topoRes.value.data)
      } else {
        setError(`Topology fetch failed: ${topoRes.reason}`)
      }

      if (sankeyRes.status === 'fulfilled') {
        setSankeyData(sankeyRes.value.data)
      } else {
        setError((prev) =>
          prev
            ? `${prev} | Trajectory fetch failed: ${sankeyRes.reason}`
            : `Trajectory fetch failed: ${sankeyRes.reason}`,
        )
      }
    } catch (err) {
      setError(`Unexpected error: ${err}`)
    } finally {
      setLoadingTopology(false)
      setLoadingSankey(false)
    }
  }, [projectId, hours])

  const isLoading = loadingTopology || loadingSankey

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Agent Graph Dashboard</span>
      </div>

      <div style={styles.controlsBar}>
        <span style={styles.label}>Project ID</span>
        <input
          style={styles.input}
          type="text"
          placeholder="my-gcp-project"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
        />
        <span style={styles.label}>Time Range</span>
        <select
          style={styles.select}
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
        >
          {hoursOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          style={
            isLoading || !projectId.trim()
              ? styles.loadButtonDisabled
              : styles.loadButton
          }
          onClick={handleLoad}
          disabled={isLoading || !projectId.trim()}
        >
          {isLoading ? 'Loading...' : 'Load'}
        </button>
      </div>

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

        {activeTab === 'topology' && (
          <>
            {topologyData ? (
              <TopologyGraph
                nodes={topologyData.nodes}
                edges={topologyData.edges}
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
    </div>
  )
}

export default App
