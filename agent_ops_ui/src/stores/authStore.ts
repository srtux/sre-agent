/**
 * Auth state store (Zustand).
 * Ported from autosre/lib/services/auth_service.dart
 */
import { create } from 'zustand'

export interface AuthUser {
  email: string
  name: string
  picture?: string
  sub: string
}

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  idToken: string | null
  isGuest: boolean
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  setUser: (user: AuthUser, accessToken: string, idToken?: string) => void
  setGuest: () => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  idToken: null,
  isGuest: false,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  setUser: (user, accessToken, idToken) =>
    set({
      user,
      accessToken,
      idToken: idToken ?? null,
      isGuest: false,
      isAuthenticated: true,
      isLoading: false,
      error: null,
    }),

  setGuest: () =>
    set({
      user: null,
      accessToken: 'dev-mode-bypass-token',
      idToken: null,
      isGuest: true,
      isAuthenticated: true,
      isLoading: false,
      error: null,
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error, isLoading: false }),

  logout: () =>
    set({
      user: null,
      accessToken: null,
      idToken: null,
      isGuest: false,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    }),
}))
