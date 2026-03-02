import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '../stores/authStore'
import { initAuth, signInWithGoogle, signInAsGuest, signOut, getAuthHeaders } from './authService'
import { useProjectStore } from '../stores/projectStore'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string): string | null => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: () => { store = {} },
  }
})()
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

describe('authService', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
    useAuthStore.setState({
      user: null, accessToken: null, idToken: null,
      isGuest: false, isAuthenticated: false, isLoading: false, error: null,
    })
    useProjectStore.setState({ projectId: '', recentProjects: [], starredProjects: [] })
  })

  describe('initAuth', () => {
    it('enters guest mode when guest_mode=true in URL', async () => {
      Object.defineProperty(window, 'location', {
        value: { search: '?guest_mode=true' }, writable: true,
      })
      await initAuth()
      expect(useAuthStore.getState().isGuest).toBe(true)
      expect(useAuthStore.getState().isAuthenticated).toBe(true)
    })

    it('restores session from localStorage', async () => {
      Object.defineProperty(window, 'location', {
        value: { search: '' }, writable: true,
      })
      const session = {
        user: { email: 'test@test.com', name: 'Test', sub: 'u1' },
        accessToken: 'tok-123',
      }
      localStorageMock.getItem.mockReturnValue(JSON.stringify(session))

      await initAuth()
      expect(useAuthStore.getState().isAuthenticated).toBe(true)
      expect(useAuthStore.getState().user?.email).toBe('test@test.com')
    })

    it('sets loading=false when no session found', async () => {
      Object.defineProperty(window, 'location', {
        value: { search: '' }, writable: true,
      })
      localStorageMock.getItem.mockReturnValue(null)

      await initAuth()
      expect(useAuthStore.getState().isLoading).toBe(false)
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })
  })

  describe('signInWithGoogle', () => {
    it('decodes JWT and sets user', async () => {
      const payload = { email: 'user@g.co', name: 'User', sub: 's1', picture: 'pic.png' }
      const b64 = btoa(JSON.stringify(payload))
      const fakeJwt = `header.${b64}.signature`

      await signInWithGoogle(fakeJwt)
      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.user?.email).toBe('user@g.co')
      expect(localStorageMock.setItem).toHaveBeenCalled()
    })

    it('sets error on invalid JWT', async () => {
      await signInWithGoogle('not-a-jwt')
      expect(useAuthStore.getState().error).toBeTruthy()
    })
  })

  describe('signInAsGuest', () => {
    it('sets guest state and removes stored session', () => {
      signInAsGuest()
      expect(useAuthStore.getState().isGuest).toBe(true)
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('sre_auth_session')
    })
  })

  describe('signOut', () => {
    it('clears auth state and localStorage', () => {
      useAuthStore.setState({ isAuthenticated: true, accessToken: 'tok' })
      signOut()
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().accessToken).toBeNull()
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('sre_auth_session')
    })
  })

  describe('getAuthHeaders', () => {
    it('returns guest headers in guest mode', () => {
      useAuthStore.setState({ isGuest: true, accessToken: 'dev-mode-bypass-token' })
      const headers = getAuthHeaders()
      expect(headers['X-Guest-Mode']).toBe('true')
      expect(headers['Authorization']).toBe('Bearer dev-mode-bypass-token')
    })

    it('returns bearer token for authenticated users', () => {
      useAuthStore.setState({ isGuest: false, accessToken: 'my-token', isAuthenticated: true })
      const headers = getAuthHeaders()
      expect(headers['Authorization']).toBe('Bearer my-token')
    })

    it('includes project ID when set', () => {
      useAuthStore.setState({ isGuest: true })
      useProjectStore.setState({ projectId: 'proj-123' })
      const headers = getAuthHeaders()
      expect(headers['X-GCP-Project-ID']).toBe('proj-123')
    })
  })
})
