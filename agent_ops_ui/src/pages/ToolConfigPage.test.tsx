import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ToolConfigPage from './ToolConfigPage'

const mockTools = [
  { name: 'fetch_traces', description: 'Fetch distributed traces', enabled: true, category: 'Investigation' },
  { name: 'analyze_metrics', description: 'Analyze metric anomalies', enabled: false, category: 'Analysis' },
  { name: 'discover_resources', description: 'Discover GCP resources', enabled: true, category: 'Discovery' },
]

const mockMutate = vi.fn()

vi.mock('../hooks/useToolConfig', () => ({
  useToolConfigs: () => ({ data: mockTools, isLoading: false, error: null }),
  useUpdateToolConfig: () => ({
    mutate: mockMutate,
    isPending: false,
    variables: null,
  }),
}))

vi.mock('../components/common/ShimmerLoading', () => ({
  default: () => <div data-testid="shimmer">Loading...</div>,
}))

vi.mock('../components/common/ErrorBanner', () => ({
  default: ({ message }: { message: string }) => <div data-testid="error-banner">{message}</div>,
}))

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('ToolConfigPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders category tab buttons', () => {
    render(<ToolConfigPage />, { wrapper })
    expect(screen.getByText('All')).toBeDefined()
    // Category names appear as both tab buttons and badges on cards; check at least one exists
    expect(screen.getAllByText('Investigation').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Analysis').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Discovery').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Remediation')).toBeDefined()
  })

  it('renders tool names and descriptions', () => {
    render(<ToolConfigPage />, { wrapper })
    expect(screen.getByText('fetch_traces')).toBeDefined()
    expect(screen.getByText('analyze_metrics')).toBeDefined()
    expect(screen.getByText('discover_resources')).toBeDefined()
  })

  it('filters tools when category tab clicked', () => {
    render(<ToolConfigPage />, { wrapper })
    // Multiple elements with 'Investigation' text; get the tab button (first one)
    fireEvent.click(screen.getAllByText('Investigation')[0])
    expect(screen.getByText('fetch_traces')).toBeDefined()
    expect(screen.queryByText('analyze_metrics')).toBeNull()
    expect(screen.queryByText('discover_resources')).toBeNull()
  })

  it('shows all tools when All tab clicked', () => {
    render(<ToolConfigPage />, { wrapper })
    fireEvent.click(screen.getAllByText('Investigation')[0])
    fireEvent.click(screen.getByText('All'))
    expect(screen.getByText('fetch_traces')).toBeDefined()
    expect(screen.getByText('analyze_metrics')).toBeDefined()
  })

  it('renders Test button for each tool', () => {
    render(<ToolConfigPage />, { wrapper })
    const testBtns = screen.getAllByText('Test')
    expect(testBtns.length).toBe(3)
  })

  it('expands tool card on click', () => {
    render(<ToolConfigPage />, { wrapper })
    fireEvent.click(screen.getByText('fetch_traces'))
    expect(screen.getByText('Enabled')).toBeDefined()
  })
})
