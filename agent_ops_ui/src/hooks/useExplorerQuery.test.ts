import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'

const mockExecuteQuery = vi.fn()
vi.mock('../api/explorer', () => ({
  executeQuery: (...args: unknown[]) => mockExecuteQuery(...args),
}))

// Must import after mock setup
import { useExplorerQuery } from './useExplorerQuery'

const store: Record<string, string> = {}
Object.defineProperty(globalThis, 'localStorage', {
  value: {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
  },
})

describe('useExplorerQuery', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    for (const key of Object.keys(store)) delete store[key]
  })

  it('starts with no results', () => {
    const { result } = renderHook(() => useExplorerQuery())
    expect(result.current.results).toBeNull()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('executes query and returns results', async () => {
    const mockResults = { columns: ['a'], rows: [{ a: 1 }] }
    mockExecuteQuery.mockResolvedValue(mockResults)

    const { result } = renderHook(() => useExplorerQuery())

    await act(async () => {
      result.current.execute('SELECT 1', 'SQL')
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.results).toEqual(mockResults)
    expect(mockExecuteQuery).toHaveBeenCalledWith('SELECT 1', 'SQL')
  })

  it('handles execution errors', async () => {
    mockExecuteQuery.mockRejectedValue(new Error('Query failed'))

    const { result } = renderHook(() => useExplorerQuery())

    await act(async () => {
      result.current.execute('BAD QUERY', 'SQL')
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.error).toBe('Query failed')
    expect(result.current.results).toBeNull()
  })

  it('clearResults resets state', async () => {
    mockExecuteQuery.mockResolvedValue({ columns: ['x'], rows: [] })

    const { result } = renderHook(() => useExplorerQuery())

    await act(async () => {
      result.current.execute('SELECT 1', 'SQL')
    })
    await waitFor(() => expect(result.current.results).not.toBeNull())

    act(() => { result.current.clearResults() })
    expect(result.current.results).toBeNull()
    expect(result.current.error).toBeNull()
  })
})
