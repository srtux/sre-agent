/**
 * Google OAuth service.
 * Ported from autosre/lib/services/auth_service.dart
 */
import { useAuthStore, type AuthUser } from '../stores/authStore'
import { useProjectStore } from '../stores/projectStore'

const AUTH_STORAGE_KEY = 'sre_auth_session'

interface StoredSession {
  user: AuthUser
  accessToken: string
  idToken?: string
}

/** Decode a JWT payload without verification (client-side display only). */
function decodeJwtPayload(token: string): Record<string, unknown> {
  const base64 = token.split('.')[1]
  const json = atob(base64.replace(/-/g, '+').replace(/_/g, '/'))
  return JSON.parse(json)
}

/** Check URL params for guest_mode and try to restore a previous session. */
export async function initAuth(): Promise<void> {
  const { setGuest, setUser, setLoading } = useAuthStore.getState()
  setLoading(true)

  const params = new URLSearchParams(window.location.search)

  // If guest_mode=true in URL, enter guest mode immediately
  if (params.get('guest_mode') === 'true') {
    setGuest()
    return
  }

  // Try to restore a previously saved session from localStorage
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    if (raw) {
      const session: StoredSession = JSON.parse(raw)
      if (session.user && session.accessToken) {
        setUser(session.user, session.accessToken, session.idToken)
        return
      }
    }
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY)
  }

  // No session found — mark loading as done, user will see login page
  setLoading(false)
}

/** Handle a Google Sign-In credential (JWT id_token). */
export async function signInWithGoogle(credential: string): Promise<void> {
  const { setUser, setError } = useAuthStore.getState()

  try {
    const payload = decodeJwtPayload(credential)

    const user: AuthUser = {
      email: (payload.email as string) || '',
      name: (payload.name as string) || (payload.email as string) || '',
      picture: (payload.picture as string) || undefined,
      sub: (payload.sub as string) || '',
    }

    // Use the credential as both access token and id token for now
    setUser(user, credential, credential)

    // Persist session
    const session: StoredSession = {
      user,
      accessToken: credential,
      idToken: credential,
    }
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session))
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Sign-in failed')
  }
}

/** Enter guest mode. */
export function signInAsGuest(): void {
  useAuthStore.getState().setGuest()
  localStorage.removeItem(AUTH_STORAGE_KEY)
}

/** Sign out and clear all stored state. */
export function signOut(): void {
  useAuthStore.getState().logout()
  localStorage.removeItem(AUTH_STORAGE_KEY)
}

/** Build auth headers for manual requests (apiClient handles this automatically). */
export function getAuthHeaders(): Record<string, string> {
  const { accessToken, isGuest } = useAuthStore.getState()
  const { projectId } = useProjectStore.getState()
  const headers: Record<string, string> = {}

  if (isGuest) {
    headers['X-Guest-Mode'] = 'true'
    headers['Authorization'] = 'Bearer dev-mode-bypass-token'
  } else if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`
  }

  if (projectId) {
    headers['X-GCP-Project-ID'] = projectId
  }

  return headers
}
