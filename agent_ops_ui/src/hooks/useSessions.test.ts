import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { useSessions, useCreateSession, useDeleteSession, useRenameSession } from './useSessions'
import { useSessionStore } from '../stores/sessionStore'

vi.mock('../api/sessions', () => ({
  listSessions: vi.fn().mockResolvedValue([
    { id: 's1', title: 'Session 1', createdAt: '2026-01-01', updatedAt: '2026-01-01' },
    { id: 's2', title: 'Session 2', createdAt: '2026-01-02', updatedAt: '2026-01-02' },
  ]),
  createSession: vi.fn().mockResolvedValue('s-new'),
  deleteSession: vi.fn().mockResolvedValue(undefined),
  renameSession: vi.fn().mockResolvedValue(undefined),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

describe('useSessions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSessionStore.setState({ sessions: [], currentSessionId: null, isLoading: false })
  })

  it('fetches sessions and updates store', async () => {
    const { result } = renderHook(() => useSessions(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data).toHaveLength(2)
    expect(useSessionStore.getState().sessions).toHaveLength(2)
  })
})

describe('useCreateSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSessionStore.setState({ sessions: [], currentSessionId: null, isLoading: false })
  })

  it('creates session and sets current', async () => {
    const { result } = renderHook(() => useCreateSession(), { wrapper: createWrapper() })
    act(() => { result.current.mutate() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(useSessionStore.getState().currentSessionId).toBe('s-new')
    expect(useSessionStore.getState().sessions).toHaveLength(1)
  })
})

describe('useDeleteSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSessionStore.setState({
      sessions: [{ id: 's1', title: 'S', createdAt: '', updatedAt: '' }],
      currentSessionId: 's1',
      isLoading: false,
    })
  })

  it('deletes session and removes from store', async () => {
    const { result } = renderHook(() => useDeleteSession(), { wrapper: createWrapper() })
    act(() => { result.current.mutate('s1') })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(useSessionStore.getState().sessions).toHaveLength(0)
  })
})

describe('useRenameSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSessionStore.setState({
      sessions: [{ id: 's1', title: 'Old', createdAt: '', updatedAt: '' }],
      currentSessionId: 's1',
      isLoading: false,
    })
  })

  it('renames session in store', async () => {
    const { result } = renderHook(() => useRenameSession(), { wrapper: createWrapper() })
    act(() => { result.current.mutate({ sessionId: 's1', title: 'Renamed' }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(useSessionStore.getState().sessions[0].title).toBe('Renamed')
  })
})
