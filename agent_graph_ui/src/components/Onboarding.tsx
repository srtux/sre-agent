import { useState } from 'react'

interface OnboardingProps {
  projectId: string;
  onSetup: (dataset: string, serviceName: string) => Promise<void>;
  loading: boolean;
  error: string | null;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    width: '100%',
    color: '#F0F4F8',
    fontFamily: "'Outfit', sans-serif",
  },
  card: {
    background: '#1E293B',
    padding: '32px',
    borderRadius: '12px',
    border: '1px solid #334155',
    width: '400px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  title: {
    fontSize: '20px',
    fontWeight: 600,
    margin: 0,
    color: '#06B6D4',
  },
  desc: {
    fontSize: '14px',
    color: '#94A3B8',
    margin: 0,
    lineHeight: '1.5',
  },
  label: {
    fontSize: '13px',
    color: '#CBD5E1',
    fontWeight: 500,
    marginBottom: '4px',
    display: 'block',
  },
  input: {
    padding: '10px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '6px',
    color: '#F0F4F8',
    fontSize: '14px',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  },
  button: {
    marginTop: '8px',
    padding: '12px',
    background: '#06B6D4',
    border: 'none',
    borderRadius: '6px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    width: '100%',
    transition: 'background 0.2s',
  },
  buttonDisabled: {
    background: 'rgba(6, 182, 212, 0.3)',
    cursor: 'not-allowed',
    color: 'rgba(255,255,255,0.5)'
  },
  error: {
    padding: '12px',
    background: 'rgba(255, 82, 82, 0.1)',
    border: '1px solid rgba(255, 82, 82, 0.3)',
    borderRadius: '6px',
    color: '#FF5252',
    fontSize: '13px',
  }
}

export default function Onboarding({ projectId, onSetup, loading, error }: OnboardingProps) {
  const [dataset, setDataset] = useState('traces')
  const [serviceName, setServiceName] = useState('sre-agent')

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Welcome to Agent Graph</h2>
        <p style={styles.desc}>
          It looks like BigQuery is not yet configured for project <strong>{projectId}</strong>.
          AutoSRE needs to create materialized views to visualize your agent traces.
        </p>

        {error && <div style={styles.error}>{error}</div>}

        <div>
          <label style={styles.label}>Trace Dataset</label>
          <input
            style={styles.input}
            value={dataset}
            onChange={e => setDataset(e.target.value)}
            placeholder="e.g. traces"
          />
        </div>

        <div>
          <label style={styles.label}>Service Name (Filter)</label>
          <input
            style={styles.input}
            value={serviceName}
            onChange={e => setServiceName(e.target.value)}
            placeholder="e.g. sre-agent"
          />
        </div>

        <button
          style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }}
          onClick={() => onSetup(dataset, serviceName)}
          disabled={loading}
        >
          {loading ? 'Configuring BigQuery...' : 'Run Setup'}
        </button>
      </div>
    </div>
  )
}
