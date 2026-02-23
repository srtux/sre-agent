import React, { useState, useCallback, useMemo } from 'react'
import type { EvalConfig } from '../../types'
import { useEvalConfigs, useDeleteEvalConfig } from '../../hooks/useEvalConfigs'
import EvalAgentCard from './EvalAgentCard'
import EvalDetailView from './EvalDetailView'
import EvalSetupWizard from './EvalSetupWizard'
import { Plus, FlaskConical } from 'lucide-react'

interface EvalsPageProps {
  hours: number
  initialAgent?: string
}

export default function EvalsPage({ hours, initialAgent }: EvalsPageProps) {
  const { data: configs, isLoading } = useEvalConfigs()
  const deleteMutation = useDeleteEvalConfig()

  const [selectedAgent, setSelectedAgent] = useState<string | null>(
    initialAgent ?? null,
  )
  const [wizardOpen, setWizardOpen] = useState(false)
  const [editingConfig, setEditingConfig] = useState<EvalConfig | undefined>(
    undefined,
  )

  const selectedConfig = useMemo(
    () => configs?.find((c) => c.agent_name === selectedAgent),
    [configs, selectedAgent],
  )

  const handleSelect = useCallback((name: string) => {
    setSelectedAgent(name)
  }, [])

  const handleBack = useCallback(() => {
    setSelectedAgent(null)
  }, [])

  const handleEdit = useCallback((config: EvalConfig) => {
    setEditingConfig(config)
    setWizardOpen(true)
  }, [])

  const handleDelete = useCallback(
    (name: string) => {
      const confirmed = window.confirm(
        `Delete evaluation configuration for "${name}"? This cannot be undone.`,
      )
      if (!confirmed) return
      deleteMutation.mutate(name)
      if (selectedAgent === name) {
        setSelectedAgent(null)
      }
    },
    [deleteMutation, selectedAgent],
  )

  const handleAddNew = useCallback(() => {
    setEditingConfig(undefined)
    setWizardOpen(true)
  }, [])

  const handleWizardClose = useCallback(() => {
    setWizardOpen(false)
    setEditingConfig(undefined)
  }, [])

  const handleWizardSaved = useCallback((agentName: string) => {
    setSelectedAgent(agentName)
  }, [])

  // --- Detail view ---
  if (selectedAgent && selectedConfig) {
    return (
      <div style={styles.page}>
        <EvalDetailView
          config={selectedConfig}
          hours={hours}
          onBack={handleBack}
          onEdit={handleEdit}
        />
        <EvalSetupWizard
          isOpen={wizardOpen}
          onClose={handleWizardClose}
          existingConfig={editingConfig}
          onSaved={handleWizardSaved}
        />
      </div>
    )
  }

  // --- List view ---
  const hasConfigs = configs && configs.length > 0

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>AI Evaluations</h1>
          <p style={styles.subtitle}>
            Configure and monitor online GenAI evaluation metrics for your
            agents.
          </p>
        </div>
        <button type="button" style={styles.addButton} onClick={handleAddNew}>
          <Plus size={16} />
          Configure Agent
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div style={styles.loadingContainer}>
          <div style={styles.spinner} />
          <span style={styles.loadingText}>Loading configurations...</span>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !hasConfigs && (
        <div style={styles.emptyState}>
          <FlaskConical size={48} color="#334155" />
          <h2 style={styles.emptyTitle}>No Evaluations Configured</h2>
          <p style={styles.emptyText}>
            Set up online GenAI evaluation to automatically score agent responses
            for coherence, groundedness, fluency, and safety.
          </p>
          <button
            type="button"
            style={styles.emptyCta}
            onClick={handleAddNew}
          >
            <Plus size={16} />
            Configure Your First Agent
          </button>
        </div>
      )}

      {/* Agent cards grid */}
      {!isLoading && hasConfigs && (
        <div style={styles.grid}>
          {configs.map((config) => (
            <EvalAgentCard
              key={config.agent_name}
              config={config}
              onSelect={handleSelect}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Wizard modal */}
      <EvalSetupWizard
        isOpen={wizardOpen}
        onClose={handleWizardClose}
        existingConfig={editingConfig}
        onSaved={handleWizardSaved}
      />
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
    fontFamily: "'Outfit', sans-serif",
    color: '#F0F4F8',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: '12px',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
    color: '#F8FAFC',
    margin: 0,
  },
  subtitle: {
    fontSize: '14px',
    color: '#94A3B8',
    margin: '4px 0 0 0',
    lineHeight: '1.5',
  },
  addButton: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 18px',
    background: '#06B6D4',
    border: 'none',
    borderRadius: '6px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.2s',
    fontFamily: 'inherit',
    flexShrink: 0,
  },
  loadingContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '60px 0',
  },
  spinner: {
    width: '20px',
    height: '20px',
    border: '2px solid #334155',
    borderTopColor: '#06B6D4',
    borderRadius: '50%',
    animation: 'echart-spin 0.7s linear infinite',
  },
  loadingText: {
    fontSize: '14px',
    color: '#64748B',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '80px 24px',
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    textAlign: 'center',
  },
  emptyTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#F8FAFC',
    margin: '8px 0 0 0',
  },
  emptyText: {
    fontSize: '14px',
    color: '#94A3B8',
    margin: 0,
    maxWidth: '420px',
    lineHeight: '1.5',
  },
  emptyCta: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 20px',
    background: '#06B6D4',
    border: 'none',
    borderRadius: '6px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: '8px',
    fontFamily: 'inherit',
    transition: 'background 0.2s',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: '16px',
  },
}
