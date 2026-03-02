/**
 * Health check polling hook.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import apiClient from '../api/client'

const POLL_INTERVAL_MS = 10_000

export function useConnectivity(): {
  isConnected: boolean
  lastChecked: Date | null
} {
  const [isConnected, setIsConnected] = useState(true)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)
  const mountedRef = useRef(true)

  const checkHealth = useCallback(async () => {
    try {
      await apiClient.get('/health', { timeout: 5000 })
      if (mountedRef.current) {
        setIsConnected(true)
        setLastChecked(new Date())
      }
    } catch {
      if (mountedRef.current) {
        setIsConnected(false)
        setLastChecked(new Date())
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    checkHealth()
    const id = setInterval(checkHealth, POLL_INTERVAL_MS)
    return () => {
      mountedRef.current = false
      clearInterval(id)
    }
  }, [checkHealth])

  return { isConnected, lastChecked }
}
