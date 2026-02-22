import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

interface OnboardingProps {
  projectId: string;
  onSetup: (dataset: string) => Promise<void>;
  loading: boolean;
  error: string | null;
}

type Phase = 'init' | 'bucket_check' | 'link_dataset' | 'poll_lro' | 'poll_verify' | 'verify_bq' | 'schema_exec' | 'success' | 'manual_input';

interface SchemaStep {
  name: string;
  label: string;
  status: 'pending' | 'running' | 'success' | 'error';
  error?: string;
  message?: string;
  retryable?: boolean;
}

interface LroOperation {
  name: string;
  done: boolean;
  error?: { message: string };
  metadata?: { createTime: string;[key: string]: unknown };
  response?: unknown;
}

const SCHEMA_STEPS: SchemaStep[] = [
  { name: 'create_dataset', label: 'Create Dataset', status: 'pending' },
  { name: 'cleanup', label: 'Cleanup Legacy Objects', status: 'pending' },
  { name: 'agent_spans_raw', label: 'Materialized View (agent_spans_raw)', status: 'pending' },
  { name: 'nodes', label: 'Topology Nodes', status: 'pending' },
  { name: 'edges', label: 'Topology Edges', status: 'pending' },
  { name: 'trajectories', label: 'Path Trajectories', status: 'pending' },
  { name: 'graph', label: 'Logical Graph', status: 'pending' },
  { name: 'hourly', label: 'Hourly Aggregation', status: 'pending' },
  { name: 'backfill', label: 'Backfill Data', status: 'pending' },
  { name: 'registries', label: 'Agent & Tool Registries', status: 'pending' },
];

export default function Onboarding({ projectId, onSetup, loading: globalLoading, error: globalError }: OnboardingProps) {
  const [phase, setPhase] = useState<Phase>('init')
  const [dataset, setDataset] = useState(() => {
    return localStorage.getItem(`agent_ops_dataset_${projectId}`) || 'traces'
  })

  const [bucketId, setBucketId] = useState<string | null>(null)
  const [, setLroName] = useState<string | null>(null)

  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [schemaSteps, setSchemaSteps] = useState<SchemaStep[]>(SCHEMA_STEPS)
  const [expandedStep, setExpandedStep] = useState<number | null>(null)
  const [lroDetails, setLroDetails] = useState<LroOperation | null>(null)

  // Ref to prevent double-execution in StrictMode
  const hasStartedRef = useRef(false)
  const isComponentMounted = useRef(true)

  useEffect(() => {
    isComponentMounted.current = true;
    return () => { isComponentMounted.current = false; };
  }, []);

  // Use this wrapper to ensure we don't update state on unmounted components
  const safeSetState = <T,>(setter: React.Dispatch<React.SetStateAction<T>>, value: React.SetStateAction<T>) => {
    if (isComponentMounted.current) {
      setter(value);
    }
  };

  const startAutoSetup = async () => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;
    safeSetState<Phase>(setPhase, 'bucket_check');
    safeSetState<string | null>(setErrorMsg, null);

    const savedSteps = localStorage.getItem(`agent_ops_schema_steps_${projectId}_${dataset}`);
    if (savedSteps) {
      try {
        const parsed = JSON.parse(savedSteps);
        if (Array.isArray(parsed) && parsed.length === SCHEMA_STEPS.length) {
          const cleanParsed = parsed.map(s => s.status === 'success' ? s : { ...s, status: 'pending', error: undefined, retryable: undefined });
          safeSetState(setSchemaSteps, cleanParsed);
        }
      } catch {
        // ignore
      }
    }

    try {
      // 1. Bucket Check
      const bucketRes = await axios.get('/api/v1/graph/setup/check_bucket', {
        params: { project_id: projectId }
      });

      const exists = bucketRes.data.exists;
      if (!exists) {
        safeSetState<string | null>(setErrorMsg, "No Observability Bucket found. Please create one in the Cloud Console.");
        safeSetState<Phase>(setPhase, 'manual_input');
        hasStartedRef.current = false;
        return;
      }

      const buckets = bucketRes.data.buckets;
      // Default to _Default or traces if available, else first one
      let defaultBucket = buckets[0].name.split('/').pop();
      for (const b of buckets) {
        if (b.name.includes('_Default') || b.name.includes('traces')) {
          defaultBucket = b.name.split('/').pop();
          break;
        }
      }
      safeSetState<string | null>(setBucketId, defaultBucket);

      // 2. See if BQ is already verified
      safeSetState<Phase>(setPhase, 'verify_bq');
      try {
        await axios.get('/api/v1/graph/setup/verify', {
          params: { project_id: projectId, dataset_id: dataset }
        });
        // BQ already verified! Jump to Schema Execc
        safeSetState<Phase>(setPhase, 'schema_exec');
        runSchemaSteps();
        return;
      } catch (e) {
        if (axios.isAxiosError(e) && e.response && e.response.status === 404) {
          // Normal, needs linking
          safeSetState<Phase>(setPhase, 'link_dataset');
          linkDataset(defaultBucket);
        } else {
          throw e; // Maybe 403, bubble up
        }
      }

    } catch (e) {
      handleError(e);
    }
  }

  const linkDataset = async (bId: string) => {
    safeSetState<Phase>(setPhase, 'link_dataset');
    safeSetState<string | null>(setErrorMsg, null);
    try {
      const res = await axios.post('/api/v1/graph/setup/link_dataset', {
        project_id: projectId,
        bucket_id: bId,
        dataset_id: dataset
      });

      if (res.data.status === 'already_linked') {
        const lid = res.data.link_id || dataset;
        setDataset(lid);
        localStorage.setItem(`agent_ops_dataset_${projectId}`, lid);
        safeSetState<Phase>(setPhase, 'poll_verify');
        pollVerify(lid);
      } else if (res.data.status === 'creating') {
        safeSetState<string | null>(setLroName, res.data.operation.name);
        safeSetState<LroOperation | null>(setLroDetails, res.data.operation);
        safeSetState<Phase>(setPhase, 'poll_lro');
        pollLro(res.data.operation.name);
      }
    } catch (e) {
      handleError(e);
    }
  }

  const pollLro = async (opName: string) => {
    if (!isComponentMounted.current) return;
    try {
      const res = await axios.get('/api/v1/graph/setup/lro_status', {
        params: { project_id: projectId, operation_name: opName }
      });

      safeSetState(setLroDetails, res.data);

      if (res.data.done) {
        if (res.data.error) {
          safeSetState<string | null>(setErrorMsg, `LRO Failed: ${res.data.error.message}`);
          safeSetState<Phase>(setPhase, 'manual_input');
        } else {
          // LRO Done! Start propagation verify
          safeSetState<Phase>(setPhase, 'poll_verify');
          pollVerify();
        }
      } else {
        // Poll again in 3s
        setTimeout(() => pollLro(opName), 3000);
      }
    } catch (e) {
      handleError(e);
    }
  }

  const pollVerify = async (dsId?: string) => {
    if (!isComponentMounted.current) return;
    const currentDs = dsId || dataset;
    try {
      await axios.get('/api/v1/graph/setup/verify', {
        params: { project_id: projectId, dataset_id: currentDs }
      });
      // Verified!
      localStorage.setItem(`agent_ops_dataset_${projectId}`, currentDs);
      safeSetState<Phase>(setPhase, 'schema_exec');
      runSchemaSteps();
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 404) {
        // Still not found, wait and retry
        setTimeout(() => pollVerify(currentDs), 10000);
      } else {
        handleError(e);
      }
    }
  }

  const runSchemaSteps = async () => {
    if (!isComponentMounted.current) return;
    safeSetState<string | null>(setErrorMsg, null);

    let currentSteps = schemaSteps;
    const saved = localStorage.getItem(`agent_ops_schema_steps_${projectId}_${dataset}`);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.length === SCHEMA_STEPS.length) currentSteps = parsed;
      } catch {
        // ignore
      }
    }

    for (let i = 0; i < currentSteps.length; i++) {
      const step = currentSteps[i];
      if (step.status === 'success') continue;

      safeSetState(setSchemaSteps, prev => {
        const next = [...prev];
        next[i].status = 'running';
        next[i].error = undefined;
        return next;
      });

      try {
        const stepRes = await axios.post(`/api/v1/graph/setup/schema/${step.name}`, {
          project_id: projectId,
          trace_dataset: dataset,
          graph_dataset: 'agentops'
        });

        safeSetState(setSchemaSteps, prev => {
          const next = [...prev];
          next[i].status = 'success';
          next[i].message = stepRes.data.message || 'Complete';
          localStorage.setItem(`agent_ops_schema_steps_${projectId}_${dataset}`, JSON.stringify(next));
          return next;
        });
      } catch (e) {
        let detail = 'Unknown error';
        const isRetryable = true; // Make ALL failed steps retryable
        if (axios.isAxiosError(e)) {
          detail = e.response?.data?.detail || e.message;
        } else if (e instanceof Error) {
          detail = e.message;
        }

        safeSetState(setSchemaSteps, prev => {
          const next = [...prev];
          next[i].status = 'error';
          next[i].error = detail;
          next[i].retryable = isRetryable;
          return next;
        });

        return; // Halt on error
      }
    }

    safeSetState<Phase>(setPhase, 'success');
  }

  const handleError = (e: unknown) => {
    let detail = String(e);
    if (axios.isAxiosError(e)) {
      detail = e.response?.data?.detail || e.message || String(e);
    } else if (e instanceof Error) {
      detail = e.message;
    }
    safeSetState<string | null>(setErrorMsg, detail);
    safeSetState<Phase>(setPhase, 'manual_input');
    hasStartedRef.current = false;
  }

  // --- RENDER HELPERS ---
  const renderIcon = (status: string) => {
    switch (status) {
      case 'pending': return <span style={{ color: '#64748B' }}>○</span>;
      case 'running': return <span className="spinner" style={{ display: 'inline-block', width: '12px', height: '12px', border: '2px solid #06B6D4', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />;
      case 'success': return <span style={{ color: '#10B981' }}>✓</span>;
      case 'error': return <span style={{ color: '#EF4444' }}>✗</span>;
      default: return null;
    }
  }

  return (
    <div style={styles.container}>
      {/* Inject css for spinner */}
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .setup-card { animation: fadeup 0.4s ease-out forwards; }
        @keyframes fadeup { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      <div style={styles.card} className="setup-card">
        <h2 style={styles.title}>Agent Graph Setup</h2>

        {globalError && <div style={styles.error}>{globalError}</div>}
        {errorMsg && phase !== 'schema_exec' && <div style={styles.error}>{errorMsg}</div>}

        {phase === 'init' && (
          <>
            <p style={styles.desc}>
              BigQuery topology objects are not configured for <strong>{projectId}</strong>.
              We can automatically configure the datasets and materialized views for you.
            </p>

            <div>
              <label style={styles.label}>Trace Dataset</label>
              <input
                style={styles.input}
                value={dataset}
                onChange={e => setDataset(e.target.value)}
                placeholder="e.g. traces"
              />
            </div>
            <button
              style={styles.button}
              onClick={startAutoSetup}
            >
              Start Automated Setup
            </button>
          </>
        )}

        {(phase === 'bucket_check' || phase === 'verify_bq') && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px 0' }}>
            {renderIcon('running')}
            <span style={styles.desc}>
              {phase === 'bucket_check' ? 'Validating Observability Bucket...' : 'Verifying BigQuery Data...'}
            </span>
          </div>
        )}

        {phase === 'link_dataset' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px 0' }}>
            {renderIcon('running')}
            <span style={styles.desc}>Creating dataset link...</span>
          </div>
        )}

        {(phase === 'poll_lro' || phase === 'poll_verify') && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px 0 8px 0' }}>
              {renderIcon('running')}
              <span style={styles.desc}>
                {phase === 'poll_lro' ? 'Provisioning BigQuery Dataset Link...' : 'Waiting for _AllSpans to propagate (Takes 1-2 mins)...'}
              </span>
            </div>
            {phase === 'poll_lro' && lroDetails && (
              <div style={styles.lroInfo}>
                <div style={styles.lroRow}>
                  <span style={styles.lroLabel}>Operation ID</span>
                  <span style={styles.lroValue}>{lroDetails.name?.split('/').pop()}</span>
                </div>
                <div style={styles.lroRow}>
                  <span style={styles.lroLabel}>Status</span>
                  <span style={{ ...styles.lroValue, color: lroDetails.done ? '#10B981' : '#F59E0B' }}>
                    {lroDetails.done ? 'Complete' : 'Provisioning...'}
                  </span>
                </div>
                {lroDetails.metadata && (
                  <div style={styles.lroRow}>
                    <span style={styles.lroLabel}>Started</span>
                    <span style={styles.lroValue}>{new Date(lroDetails.metadata.createTime).toLocaleTimeString()}</span>
                  </div>
                )}
                {lroDetails.error && (
                  <div style={{ ...styles.lroRow, borderTop: '1px solid rgba(239, 68, 68, 0.2)', paddingTop: '8px', marginTop: '8px' }}>
                    <span style={{ ...styles.lroValue, color: '#EF4444' }}>{lroDetails.error.message}</span>
                  </div>
                )}
              </div>
            )}
            <div style={styles.progressBarBg}>
              <div style={{ ...styles.progressBarFill, width: lroDetails?.done ? '100%' : '50%' }}></div>
            </div>
            {lroDetails?.error && (
              <button
                style={{ ...styles.button, marginTop: '16px', background: '#EF4444' }}
                onClick={() => linkDataset(bucketId || 'traces')}
              >
                Retry Link Creation
              </button>
            )}
          </div>
        )}

        {phase === 'schema_exec' && (
          <div style={styles.terminal}>
            <div style={styles.terminalHeader}>Schema Execution</div>
            <div style={styles.terminalBody}>
              {schemaSteps.map((step, idx) => (
                <div key={idx} style={{ marginBottom: '8px' }}>
                  <div
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#E2E8F0', cursor: 'pointer', padding: '4px', borderRadius: '4px', background: expandedStep === idx ? 'rgba(255,255,255,0.05)' : 'transparent' }}
                    onClick={() => setExpandedStep(expandedStep === idx ? null : idx)}
                  >
                    {renderIcon(step.status)}
                    <span style={{ flex: 1 }}>{step.label}</span>
                    <span style={{ fontSize: '10px', color: '#64748B' }}>
                      {expandedStep === idx ? '▲' : '▼'}
                    </span>
                  </div>
                  {expandedStep === idx && (
                    <div style={{ ...styles.schemaDetails, marginTop: '4px', fontSize: '12px', marginLeft: '24px', color: '#94A3B8' }}>
                      {step.status === 'pending' && <div>Waiting to execute...</div>}
                      {step.status === 'running' && <div>Executing DDL in BigQuery...</div>}
                      {step.status === 'success' && <div style={{ color: '#10B981' }}>{step.message || 'Operation successful'}</div>}
                      {step.error && (
                        <div style={styles.schemaError}>
                          <div style={{ color: '#EF4444', marginBottom: '8px' }}>{step.error}</div>
                          {step.retryable && (
                            <button
                              style={styles.retryButton}
                              onClick={() => {
                                safeSetState(setSchemaSteps, prev => {
                                  const next = [...prev];
                                  next[idx].status = 'pending';
                                  return next;
                                });
                                runSchemaSteps();
                              }}
                            >
                              Retry Failed Step
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {phase === 'success' && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <div style={{ fontSize: '48px', color: '#10B981', marginBottom: '16px' }}>✓</div>
            <h3 style={{ ...styles.title, color: '#F8FAFC', marginBottom: '8px' }}>Setup Complete!</h3>
            <p style={styles.desc}>Agent graph data is now flowing into BigQuery.</p>
            <button
              style={{ ...styles.button, marginTop: '24px' }}
              onClick={() => onSetup(dataset)}
              disabled={globalLoading}
            >
              {globalLoading ? 'Loading Graph...' : 'Open Agent Graph'}
            </button>
          </div>
        )}

        {phase === 'manual_input' && (
          <button
            style={{ ...styles.button, background: '#334155' }}
            onClick={() => {
              setPhase('init');
              hasStartedRef.current = false;
            }}
          >
            Start Over
          </button>
        )}

      </div>
    </div>
  )
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
    width: '450px',
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
    lineHeight: '1.5',
  },
  progressBarBg: {
    width: '100%',
    height: '6px',
    background: '#334155',
    borderRadius: '3px',
    overflow: 'hidden',
    marginTop: '8px'
  },
  progressBarFill: {
    height: '100%',
    background: '#06B6D4',
    width: '50%',
    animation: 'pulse-width 2s ease-in-out infinite alternate'
  },
  terminal: {
    background: '#0F172A',
    borderRadius: '8px',
    border: '1px solid #334155',
    overflow: 'hidden',
    marginTop: '8px'
  },
  terminalHeader: {
    background: '#1E293B',
    padding: '8px 12px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#94A3B8',
    borderBottom: '1px solid #334155',
  },
  terminalBody: {
    padding: '12px',
    maxHeight: '250px',
    overflowY: 'auto'
  },
  schemaError: {
    background: 'rgba(239, 68, 68, 0.1)',
    borderLeft: '2px solid #EF4444',
    margin: '8px 0',
    padding: '8px 12px',
    fontSize: '12px',
    borderRadius: '0 4px 4px 0'
  },
  schemaDetails: {
    padding: '8px',
    background: '#1E293B',
    borderRadius: '4px',
    border: '1px solid #334155'
  },
  retryButton: {
    padding: '6px 12px',
    background: '#334155',
    border: '1px solid #475569',
    borderRadius: '4px',
    color: '#F8FAFC',
    fontSize: '12px',
    cursor: 'pointer',
  },
  lroInfo: {
    background: 'rgba(15, 23, 42, 0.5)',
    border: '1px solid rgba(51, 65, 85, 0.5)',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '16px',
    fontSize: '13px',
    fontFamily: 'monospace',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  lroRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  lroLabel: {
    color: '#64748B',
    marginRight: '12px'
  },
  lroValue: {
    color: '#E2E8F0',
    textAlign: 'right'
  }
}
