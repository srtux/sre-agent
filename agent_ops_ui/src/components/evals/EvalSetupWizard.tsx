import { useState, useEffect, useCallback } from 'react'
import type { EvalConfig } from '../../types'
import { useUpsertEvalConfig } from '../../hooks/useEvalConfigs'
import { useAgentContext } from '../../contexts/AgentContext'

const AVAILABLE_METRICS = [
  { key: 'coherence', label: 'Coherence', description: 'Logical consistency of responses' },
  { key: 'groundedness', label: 'Groundedness', description: 'Factual accuracy and evidence' },
  { key: 'fluency', label: 'Fluency', description: 'Language quality and readability' },
  { key: 'safety', label: 'Safety', description: 'Harmful content detection' },
] as const

type MetricKey = (typeof AVAILABLE_METRICS)[number]['key']

interface EvalSetupWizardProps {
  isOpen: boolean
  onClose: () => void
  initialAgentName?: string
  existingConfig?: EvalConfig
  onSaved?: (agentName: string) => void
}

export default function EvalSetupWizard({
  isOpen,
  onClose,
  initialAgentName,
  existingConfig,
  onSaved,
}: EvalSetupWizardProps) {
  const { availableAgents } = useAgentContext()
  const upsertMutation = useUpsertEvalConfig()

  const isEditMode = !!existingConfig

  const [step, setStep] = useState<1 | 2>(1)
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [enabledMetrics, setEnabledMetrics] = useState<Set<MetricKey>>(
    new Set(['coherence', 'groundedness', 'fluency', 'safety']),
  )
  const [samplingRate, setSamplingRate] = useState<number>(100)

  // Reset form state when modal opens or props change
  useEffect(() => {
    if (!isOpen) return
    setStep(1)
    upsertMutation.reset()

    if (existingConfig) {
      setSelectedAgent(existingConfig.agent_name)
      const metricSet = new Set<MetricKey>()
      for (const m of existingConfig.metrics) {
        if (AVAILABLE_METRICS.some((am) => am.key === m)) {
          metricSet.add(m as MetricKey)
        }
      }
      setEnabledMetrics(metricSet)
      setSamplingRate(Math.round(existingConfig.sampling_rate * 100))
    } else {
      setSelectedAgent(initialAgentName ?? '')
      setEnabledMetrics(new Set(['coherence', 'groundedness', 'fluency', 'safety']))
      setSamplingRate(100)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, existingConfig, initialAgentName])

  const toggleMetric = useCallback((key: MetricKey) => {
    setEnabledMetrics((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }, [])

  const canProceed = selectedAgent !== '' && enabledMetrics.size > 0

  const handleSave = useCallback(async () => {
    if (!selectedAgent) return
    try {
      await upsertMutation.mutateAsync({
        agentName: selectedAgent,
        isEnabled: true,
        samplingRate: samplingRate / 100,
        metrics: Array.from(enabledMetrics),
      })
      onSaved?.(selectedAgent)
      onClose()
    } catch {
      // Error is captured by mutation state
    }
  }, [selectedAgent, samplingRate, enabledMetrics, upsertMutation, onSaved, onClose])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) {
        onClose()
      }
    },
    [onClose],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Escape') {
        onClose()
      }
    },
    [onClose],
  )

  if (!isOpen) return null

  const displayAgent =
    availableAgents.find((a) => a.serviceName === selectedAgent)?.agentName ??
    selectedAgent

  return (
    <div
      style={styles.overlay}
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-label={isEditMode ? 'Edit eval configuration' : 'Set up eval configuration'}
      tabIndex={-1}
    >
      <div style={styles.card}>
        {/* Step indicator */}
        <div style={styles.stepIndicator}>
          <span style={step === 1 ? styles.stepActive : styles.stepInactive}>
            1. Configure
          </span>
          <span style={styles.stepArrow}>&rarr;</span>
          <span style={step === 2 ? styles.stepActive : styles.stepInactive}>
            2. Confirm
          </span>
        </div>

        {step === 1 && (
          <div style={styles.stepContent}>
            <h2 style={styles.title}>
              {isEditMode ? 'Edit Eval Configuration' : 'Set Up Evaluation'}
            </h2>
            <p style={styles.desc}>
              Configure online GenAI evaluation for an agent.
            </p>

            {/* Agent selector */}
            <div style={styles.fieldGroup}>
              <label style={styles.label} htmlFor="eval-agent-select">
                Agent
              </label>
              <select
                id="eval-agent-select"
                style={{
                  ...styles.select,
                  ...(isEditMode ? styles.selectDisabled : {}),
                }}
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                disabled={isEditMode}
              >
                <option value="">Select an agent...</option>
                {availableAgents.map((agent) => (
                  <option key={agent.serviceName} value={agent.serviceName}>
                    {agent.agentName || agent.serviceName}
                  </option>
                ))}
              </select>
            </div>

            {/* Metric toggles */}
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Metrics</label>
              <div style={styles.metricsGrid}>
                {AVAILABLE_METRICS.map((metric) => {
                  const isEnabled = enabledMetrics.has(metric.key)
                  return (
                    <button
                      key={metric.key}
                      type="button"
                      style={{
                        ...styles.metricToggle,
                        ...(isEnabled
                          ? styles.metricToggleOn
                          : styles.metricToggleOff),
                      }}
                      onClick={() => toggleMetric(metric.key)}
                      aria-pressed={isEnabled}
                    >
                      <span style={styles.metricLabel}>{metric.label}</span>
                      <span style={styles.metricDesc}>{metric.description}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Sampling rate slider */}
            <div style={styles.fieldGroup}>
              <label style={styles.label} htmlFor="eval-sampling-rate">
                Sampling Rate: {samplingRate}%
              </label>
              <input
                id="eval-sampling-rate"
                type="range"
                min={0}
                max={100}
                step={1}
                value={samplingRate}
                onChange={(e) => setSamplingRate(Number(e.target.value))}
                style={styles.slider}
              />
              <div style={styles.sliderLabels}>
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            {/* Next button */}
            <button
              type="button"
              style={{
                ...styles.button,
                ...(!canProceed ? styles.buttonDisabled : {}),
              }}
              disabled={!canProceed}
              onClick={() => setStep(2)}
            >
              Next
            </button>
          </div>
        )}

        {step === 2 && (
          <div style={styles.stepContent}>
            <h2 style={styles.title}>Confirm Configuration</h2>
            <p style={styles.desc}>
              Review and save your evaluation settings.
            </p>

            {/* Summary card */}
            <div style={styles.summaryCard}>
              <div style={styles.summaryRow}>
                <span style={styles.summaryLabel}>Agent</span>
                <span style={styles.summaryValue}>{displayAgent}</span>
              </div>
              <div style={styles.summaryRow}>
                <span style={styles.summaryLabel}>Metrics</span>
                <span style={styles.summaryValue}>
                  {Array.from(enabledMetrics).join(', ')}
                </span>
              </div>
              <div style={styles.summaryRow}>
                <span style={styles.summaryLabel}>Sampling Rate</span>
                <span style={styles.summaryValue}>{samplingRate}%</span>
              </div>
            </div>

            {/* Error display */}
            {upsertMutation.isError && (
              <div style={styles.error}>
                {upsertMutation.error instanceof Error
                  ? upsertMutation.error.message
                  : 'Failed to save configuration. Please try again.'}
              </div>
            )}

            {/* Action buttons */}
            <div style={styles.actionRow}>
              <button
                type="button"
                style={styles.backButton}
                onClick={() => setStep(1)}
                disabled={upsertMutation.isPending}
              >
                Back
              </button>
              <button
                type="button"
                style={{
                  ...styles.button,
                  flex: 1,
                  ...(upsertMutation.isPending ? styles.buttonDisabled : {}),
                }}
                disabled={upsertMutation.isPending}
                onClick={handleSave}
              >
                {upsertMutation.isPending ? 'Saving...' : 'Save & Enable'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  card: {
    background: '#1E293B',
    borderRadius: '12px',
    border: '1px solid #334155',
    width: '480px',
    maxWidth: '95vw',
    maxHeight: '90vh',
    overflowY: 'auto',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
    padding: '28px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    fontFamily: "'Outfit', sans-serif",
    color: '#F0F4F8',
  },
  stepIndicator: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    paddingBottom: '16px',
    borderBottom: '1px solid #334155',
    marginBottom: '8px',
  },
  stepActive: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#06B6D4',
  },
  stepInactive: {
    fontSize: '13px',
    fontWeight: 400,
    color: '#64748B',
  },
  stepArrow: {
    fontSize: '13px',
    color: '#475569',
  },
  stepContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    paddingTop: '8px',
  },
  title: {
    fontSize: '20px',
    fontWeight: 600,
    margin: 0,
    color: '#F8FAFC',
  },
  desc: {
    fontSize: '14px',
    color: '#94A3B8',
    margin: 0,
    lineHeight: '1.5',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '13px',
    fontWeight: 500,
    color: '#CBD5E1',
  },
  select: {
    padding: '10px 12px',
    background: '#0F172A',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#F0F4F8',
    fontSize: '14px',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box' as const,
    cursor: 'pointer',
    appearance: 'auto' as const,
  },
  selectDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
  },
  metricToggle: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'flex-start',
    gap: '2px',
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid',
    cursor: 'pointer',
    transition: 'all 0.2s',
    textAlign: 'left' as const,
    fontFamily: 'inherit',
  },
  metricToggleOn: {
    background: 'rgba(6, 182, 212, 0.1)',
    borderColor: '#06B6D4',
    color: '#F0F4F8',
  },
  metricToggleOff: {
    background: 'transparent',
    borderColor: '#334155',
    color: '#94A3B8',
  },
  metricLabel: {
    fontSize: '13px',
    fontWeight: 600,
  },
  metricDesc: {
    fontSize: '11px',
    opacity: 0.7,
  },
  slider: {
    width: '100%',
    accentColor: '#06B6D4',
    cursor: 'pointer',
  },
  sliderLabels: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '11px',
    color: '#64748B',
  },
  button: {
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
    fontFamily: 'inherit',
  },
  buttonDisabled: {
    background: 'rgba(6, 182, 212, 0.3)',
    cursor: 'not-allowed',
    color: 'rgba(255, 255, 255, 0.5)',
  },
  summaryCard: {
    background: '#0F172A',
    borderRadius: '8px',
    border: '1px solid #334155',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  summaryRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  summaryLabel: {
    fontSize: '13px',
    color: '#64748B',
    flexShrink: 0,
    marginRight: '12px',
  },
  summaryValue: {
    fontSize: '13px',
    color: '#F0F4F8',
    fontWeight: 500,
    textAlign: 'right' as const,
  },
  error: {
    padding: '12px',
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '6px',
    color: '#EF4444',
    fontSize: '13px',
    lineHeight: '1.5',
  },
  actionRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
  },
  backButton: {
    padding: '12px 20px',
    background: 'transparent',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#CBD5E1',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontFamily: 'inherit',
  },
}
