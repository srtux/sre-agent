import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LoginPage } from './LoginPage'
import { useAuthStore } from '../stores/authStore'

vi.mock('../components/auth/GoogleSignInButton', () => ({
  GoogleSignInButton: () => <div data-testid="google-btn">GoogleSignIn</div>,
}))

const mockSignInAsGuest = vi.fn()
vi.mock('../services/authService', () => ({
  signInAsGuest: () => mockSignInAsGuest(),
}))

describe('LoginPage', () => {
  beforeEach(() => {
    useAuthStore.setState({ error: null, isLoading: false })
    vi.clearAllMocks()
  })

  it('renders login page with Google sign-in and guest mode', () => {
    render(<LoginPage />)
    expect(screen.getByTestId('google-btn')).toBeDefined()
    expect(screen.getByText(/guest/i)).toBeDefined()
  })

  it('calls signInAsGuest when guest button clicked', () => {
    render(<LoginPage />)
    const guestBtn = screen.getByText(/guest/i)
    fireEvent.click(guestBtn)
    expect(mockSignInAsGuest).toHaveBeenCalled()
  })

  it('displays auth error when present', () => {
    useAuthStore.setState({ error: 'Invalid credentials' })
    render(<LoginPage />)
    expect(screen.getByText('Invalid credentials')).toBeDefined()
  })
})
