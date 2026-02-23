import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EvalsPage from './EvalsPage'

// --- Mocks ---

const mockUseEvalConfigs = vi.fn()
const mockDeleteMutate = vi.fn()

vi.mock('../../hooks/useEvalConfigs', () => ({
  useEvalConfigs: (...args: unknown[]) => mockUseEvalConfigs(...args),
  useDeleteEvalConfig: vi.fn(() => ({ mutate: mockDeleteMutate })),
  useUpsertEvalConfig: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}))

vi.mock('./EvalAgentCard', () => ({
  default: function MockCard({
    config,
    onSelect,
  }: {
    config: { agent_name: string }
    onSelect: (n: string) => void
  }) {
    return (
      <div
        data-testid={`agent-card-${config.agent_name}`}
        onClick={() => onSelect(config.agent_name)}
      >
        {config.agent_name}
      </div>
    )
  },
}))

vi.mock('./EvalDetailView', () => ({
  default: function MockDetail({
    config,
    onBack,
  }: {
    config: { agent_name: string }
    onBack: () => void
  }) {
    return (
      <div data-testid="detail-view">
        <button onClick={onBack}>Back</button>
        {config.agent_name}
      </div>
    )
  },
}))

vi.mock('./EvalSetupWizard', () => ({
  default: function MockWizard({ isOpen }: { isOpen: boolean }) {
    return isOpen ? <div data-testid="wizard">Wizard</div> : null
  },
}))

vi.mock('../../contexts/AgentContext', () => ({
  useAgentContext: () => ({
    projectId: 'test-project',
    serviceName: '',
    setServiceName: vi.fn(),
    availableAgents: [],
    loadingAgents: false,
    errorAgents: null,
  }),
}))

// --- Helpers ---

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  )
}

const MOCK_CONFIGS = [
  {
    agent_name: 'agent-alpha',
    is_enabled: true,
    sampling_rate: 0.5,
    metrics: ['coherence', 'fluency'],
    last_eval_timestamp: null,
  },
  {
    agent_name: 'agent-beta',
    is_enabled: false,
    sampling_rate: 1.0,
    metrics: ['safety'],
    last_eval_timestamp: '2026-02-20T10:00:00Z',
  },
]

// --- Tests ---

describe('EvalsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows empty state when no configs', () => {
    mockUseEvalConfigs.mockReturnValue({ data: [], isLoading: false })
    renderWithQuery(<EvalsPage hours={24} />)

    expect(screen.getByText('No Evaluations Configured')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    mockUseEvalConfigs.mockReturnValue({ data: undefined, isLoading: true })
    renderWithQuery(<EvalsPage hours={24} />)

    expect(screen.getByText('Loading configurations...')).toBeInTheDocument()
  })

  it('renders agent cards when configs exist', () => {
    mockUseEvalConfigs.mockReturnValue({
      data: MOCK_CONFIGS,
      isLoading: false,
    })
    renderWithQuery(<EvalsPage hours={24} />)

    expect(screen.getByTestId('agent-card-agent-alpha')).toBeInTheDocument()
    expect(screen.getByTestId('agent-card-agent-beta')).toBeInTheDocument()
  })

  it('navigates to detail view on card click', () => {
    mockUseEvalConfigs.mockReturnValue({
      data: MOCK_CONFIGS,
      isLoading: false,
    })
    renderWithQuery(<EvalsPage hours={24} />)

    fireEvent.click(screen.getByTestId('agent-card-agent-alpha'))

    expect(screen.getByTestId('detail-view')).toBeInTheDocument()
    expect(screen.getByText('agent-alpha')).toBeInTheDocument()
  })

  it('shows Configure Agent button', () => {
    mockUseEvalConfigs.mockReturnValue({ data: [], isLoading: false })
    renderWithQuery(<EvalsPage hours={24} />)

    expect(
      screen.getByRole('button', { name: /Configure Agent/i }),
    ).toBeInTheDocument()
  })

  it('opens wizard on Configure Agent button click', () => {
    mockUseEvalConfigs.mockReturnValue({ data: [], isLoading: false })
    renderWithQuery(<EvalsPage hours={24} />)

    // Wizard should not be visible before click
    expect(screen.queryByTestId('wizard')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Configure Agent/i }))

    expect(screen.getByTestId('wizard')).toBeInTheDocument()
  })
})
