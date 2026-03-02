/**
 * Google Sign-In button using @react-oauth/google.
 */
import React, { useState } from 'react'
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google'
import { signInWithGoogle } from '../../services/authService'
import { colors, typography, spacing } from '../../theme/tokens'

export const GoogleSignInButton: React.FC = () => {
  const [error, setError] = useState<string | null>(null)

  const handleSuccess = async (response: CredentialResponse) => {
    setError(null)
    if (response.credential) {
      await signInWithGoogle(response.credential)
    } else {
      setError('No credential received from Google')
    }
  }

  const handleError = () => {
    setError('Google Sign-In failed. Please try again.')
  }

  return (
    <div style={styles.container}>
      <GoogleLogin
        onSuccess={handleSuccess}
        onError={handleError}
        theme="filled_black"
        size="large"
        width="280"
        shape="pill"
      />
      {error && <p style={styles.error}>{error}</p>}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: spacing.sm,
  },
  error: {
    color: colors.error,
    fontSize: typography.sizes.sm,
    margin: 0,
  },
}
