import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePromptHistory } from './usePromptHistory'

const store: Record<string, string> = {}
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { store[key] = value }),
  removeItem: vi.fn((key: string) => { delete store[key] }),
}
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

describe('usePromptHistory', () => {
  beforeEach(() => {
    for (const key of Object.keys(store)) delete store[key]
    vi.clearAllMocks()
  })

  it('add stores prompts and navigateUp retrieves them', () => {
    const { result } = renderHook(() => usePromptHistory())

    act(() => { result.current.add('prompt 1') })
    act(() => { result.current.add('prompt 2') })
    act(() => { result.current.add('prompt 3') })

    let val: string | null = null
    act(() => { val = result.current.navigateUp() })
    expect(val).toBe('prompt 3')

    act(() => { val = result.current.navigateUp() })
    expect(val).toBe('prompt 2')

    act(() => { val = result.current.navigateUp() })
    expect(val).toBe('prompt 1')
  })

  it('navigateDown goes forward in history', () => {
    const { result } = renderHook(() => usePromptHistory())

    act(() => { result.current.add('a') })
    act(() => { result.current.add('b') })

    let val: string | null = null
    act(() => { result.current.navigateUp() }) // b
    act(() => { result.current.navigateUp() }) // a
    act(() => { val = result.current.navigateDown() }) // b
    expect(val).toBe('b')
  })

  it('navigateDown returns null when past end of history', () => {
    const { result } = renderHook(() => usePromptHistory())

    act(() => { result.current.add('x') })

    let val: string | null = null
    act(() => { result.current.navigateUp() }) // x
    act(() => { val = result.current.navigateDown() }) // past end
    expect(val).toBeNull()
  })

  it('navigateUp returns null for empty history', () => {
    const { result } = renderHook(() => usePromptHistory())
    let val: string | null = 'not-null'
    act(() => { val = result.current.navigateUp() })
    expect(val).toBeNull()
  })

  it('does not add duplicate of last entry', () => {
    const { result } = renderHook(() => usePromptHistory())

    act(() => { result.current.add('same') })
    act(() => { result.current.add('same') })

    const raw = JSON.parse(store['sre_prompt_history'] ?? '[]')
    expect(raw.filter((s: string) => s === 'same')).toHaveLength(1)
  })
})
