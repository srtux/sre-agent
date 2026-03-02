import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HelpPage from './HelpPage'

const mockItems = [
  { id: '1', title: 'Getting Started', description: 'Intro guide', content: 'Full content here', category: 'General' },
  { id: '2', title: 'Trace Analysis', description: 'How to analyze traces', content: 'Trace details', category: 'Investigation' },
  { id: '3', title: 'Alert Setup', description: 'Configure alerts', content: 'Alert content', category: 'General' },
]

vi.mock('../hooks/useHelp', () => ({
  useHelp: () => ({ data: mockItems, isLoading: false, error: null }),
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

describe('HelpPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders help article titles', () => {
    render(<HelpPage />, { wrapper })
    expect(screen.getByText('Getting Started')).toBeDefined()
    expect(screen.getByText('Trace Analysis')).toBeDefined()
    expect(screen.getByText('Alert Setup')).toBeDefined()
  })

  it('renders category buttons from data', () => {
    render(<HelpPage />, { wrapper })
    expect(screen.getByText('All')).toBeDefined()
    // 'General' appears as category button and as badges on cards; check at least one exists
    expect(screen.getAllByText('General').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Investigation').length).toBeGreaterThanOrEqual(1)
  })

  it('renders search input', () => {
    render(<HelpPage />, { wrapper })
    expect(screen.getByPlaceholderText('Search help articles...')).toBeDefined()
  })

  it('filters articles by search text', () => {
    render(<HelpPage />, { wrapper })
    fireEvent.change(screen.getByPlaceholderText('Search help articles...'), {
      target: { value: 'trace' },
    })
    expect(screen.getByText('Trace Analysis')).toBeDefined()
    expect(screen.queryByText('Getting Started')).toBeNull()
  })

  it('expands card on click to show content', () => {
    render(<HelpPage />, { wrapper })
    fireEvent.click(screen.getByText('Getting Started'))
    expect(screen.getByText('Full content here')).toBeDefined()
  })

  it('collapses card on second click', () => {
    render(<HelpPage />, { wrapper })
    fireEvent.click(screen.getByText('Getting Started'))
    expect(screen.getByText('Full content here')).toBeDefined()
    fireEvent.click(screen.getByText('Getting Started'))
    expect(screen.queryByText('Full content here')).toBeNull()
  })
})
