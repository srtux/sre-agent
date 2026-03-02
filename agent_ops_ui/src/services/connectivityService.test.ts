import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useConnectivity } from './connectivityService'

const mockGet = vi.fn()
vi.mock('../api/client', () => ({
  default: { get: (...args: unknown[]) => mockGet(...args) },
}))

describe('useConnectivity', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('starts as connected when health check succeeds', async () => {
    mockGet.mockResolvedValue({ status: 200 })
    const { result } = renderHook(() => useConnectivity())
    await waitFor(() => expect(result.current.isConnected).toBe(true))
    expect(result.current.lastChecked).not.toBeNull()
  })

  it('sets disconnected when health check fails', async () => {
    mockGet.mockRejectedValue(new Error('Network error'))
    const { result } = renderHook(() => useConnectivity())
    await waitFor(() => expect(result.current.isConnected).toBe(false))
  })

  it('calls health endpoint with timeout', async () => {
    mockGet.mockResolvedValue({ status: 200 })
    renderHook(() => useConnectivity())
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(mockGet).toHaveBeenCalledWith('/health', { timeout: 5000 })
  })
})
