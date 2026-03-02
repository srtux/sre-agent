/**
 * Convenience hook for auth state.
 */
import { useAuthStore } from '../stores/authStore'
import { signOut } from '../services/authService'

export function useAuth() {
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const isGuest = useAuthStore((s) => s.isGuest)
  const isLoading = useAuthStore((s) => s.isLoading)
  const error = useAuthStore((s) => s.error)

  return { user, isAuthenticated, isGuest, isLoading, error, signOut }
}
