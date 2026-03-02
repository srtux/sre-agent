import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SessionPanel } from './SessionPanel'
import { useSessionStore } from '../../stores/sessionStore'

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    data: [
      { id: 's1', title: 'Latency Investigation', createdAt: '2026-01-01', updatedAt: '2026-01-01' },
      { id: 's2', title: 'Error Spike', createdAt: '2026-01-02', updatedAt: '2026-01-02' },
    ],
    isLoading: false,
  }),
  useCreateSession: () => ({ mutate: vi.fn() }),
  useDeleteSession: () => ({ mutate: vi.fn() }),
  useRenameSession: () => ({ mutate: vi.fn() }),
}))

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('SessionPanel', () => {
  beforeEach(() => {
    useSessionStore.setState({ sessions: [], currentSessionId: 's1', isLoading: false })
  })

  it('renders session list', () => {
    render(<SessionPanel />, { wrapper })
    expect(screen.getByText('Latency Investigation')).toBeDefined()
    expect(screen.getByText('Error Spike')).toBeDefined()
  })

  it('renders Sessions header', () => {
    render(<SessionPanel />, { wrapper })
    expect(screen.getByText('Sessions')).toBeDefined()
  })

  it('clicking a session sets it as current', () => {
    render(<SessionPanel />, { wrapper })
    const sessionItem = screen.getByText('Error Spike')
    fireEvent.click(sessionItem)
    expect(useSessionStore.getState().currentSessionId).toBe('s2')
  })
})
