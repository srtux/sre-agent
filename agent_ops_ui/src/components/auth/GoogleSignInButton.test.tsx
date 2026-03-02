import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GoogleSignInButton } from './GoogleSignInButton'

vi.mock('@react-oauth/google', () => ({
  GoogleLogin: (props: { onSuccess: (...args: unknown[]) => void; onError: (...args: unknown[]) => void }) => (
    <button data-testid="google-login" onClick={() => props.onError()}>
      Sign in with Google
    </button>
  ),
}))

vi.mock('../../services/authService', () => ({
  signInWithGoogle: vi.fn(),
}))

describe('GoogleSignInButton', () => {
  it('renders the Google login button', () => {
    render(<GoogleSignInButton />)
    expect(screen.getByTestId('google-login')).toBeDefined()
    expect(screen.getByText('Sign in with Google')).toBeDefined()
  })

  it('shows error on sign-in failure', async () => {
    render(<GoogleSignInButton />)
    const btn = screen.getByTestId('google-login')
    btn.click()
    expect(await screen.findByText('Google Sign-In failed. Please try again.')).toBeDefined()
  })
})
