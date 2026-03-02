import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useAuth } from './useAuth'
import { useAuthStore } from '../stores/authStore'

vi.mock('../services/authService', () => ({
  signOut: vi.fn(),
}))

describe('useAuth', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null, accessToken: null, idToken: null,
      isGuest: false, isAuthenticated: false, isLoading: false, error: null,
    })
  })

  it('returns unauthenticated state by default', () => {
    const { result } = renderHook(() => useAuth())
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(result.current.isGuest).toBe(false)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(typeof result.current.signOut).toBe('function')
  })

  it('reflects authenticated state', () => {
    useAuthStore.setState({
      user: { email: 'a@b.com', name: 'A', sub: 'u1' },
      accessToken: 'tok',
      isAuthenticated: true,
    })
    const { result } = renderHook(() => useAuth())
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user?.email).toBe('a@b.com')
  })

  it('reflects guest state', () => {
    useAuthStore.setState({ isGuest: true, isAuthenticated: true })
    const { result } = renderHook(() => useAuth())
    expect(result.current.isGuest).toBe(true)
    expect(result.current.isAuthenticated).toBe(true)
  })

  it('reflects error state', () => {
    useAuthStore.setState({ error: 'Auth failed' })
    const { result } = renderHook(() => useAuth())
    expect(result.current.error).toBe('Auth failed')
  })
})
