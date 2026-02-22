import { renderHook, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { type ReactNode } from 'react'
import {
  DashboardFilterProvider,
  useDashboardFilters,
  type TimeRange,
} from './DashboardFilterContext'

function createWrapper(initialFilters?: { timeRange?: TimeRange; selectedAgents?: string[]; groupByAgent?: boolean }) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <DashboardFilterProvider initialFilters={initialFilters}>
        {children}
      </DashboardFilterProvider>
    )
  }
}

describe('DashboardFilterContext', () => {
  it('provides default filter values', () => {
    const { result } = renderHook(() => useDashboardFilters(), {
      wrapper: createWrapper(),
    })

    expect(result.current.timeRange).toBe('24h')
    expect(result.current.selectedAgents).toEqual([])
    expect(result.current.groupByAgent).toBe(false)
  })

  it('accepts initial filter overrides', () => {
    const { result } = renderHook(() => useDashboardFilters(), {
      wrapper: createWrapper({ timeRange: '7d', groupByAgent: true }),
    })

    expect(result.current.timeRange).toBe('7d')
    expect(result.current.groupByAgent).toBe(true)
  })

  it('updates time range', () => {
    const { result } = renderHook(() => useDashboardFilters(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.setTimeRange('1h')
    })

    expect(result.current.timeRange).toBe('1h')
  })

  it('updates selected agents', () => {
    const { result } = renderHook(() => useDashboardFilters(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.setSelectedAgents(['agent-a', 'agent-b'])
    })

    expect(result.current.selectedAgents).toEqual(['agent-a', 'agent-b'])
  })

  it('toggles agent selection on and off', () => {
    const { result } = renderHook(() => useDashboardFilters(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.toggleAgent('agent-a')
    })
    expect(result.current.selectedAgents).toEqual(['agent-a'])

    act(() => {
      result.current.toggleAgent('agent-b')
    })
    expect(result.current.selectedAgents).toEqual(['agent-a', 'agent-b'])

    act(() => {
      result.current.toggleAgent('agent-a')
    })
    expect(result.current.selectedAgents).toEqual(['agent-b'])
  })

  it('updates groupByAgent', () => {
    const { result } = renderHook(() => useDashboardFilters(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.setGroupByAgent(true)
    })

    expect(result.current.groupByAgent).toBe(true)
  })

  it('resets filters to defaults', () => {
    const { result } = renderHook(() => useDashboardFilters(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.setTimeRange('7d')
      result.current.setSelectedAgents(['agent-a'])
      result.current.setGroupByAgent(true)
    })

    act(() => {
      result.current.resetFilters()
    })

    expect(result.current.timeRange).toBe('24h')
    expect(result.current.selectedAgents).toEqual([])
    expect(result.current.groupByAgent).toBe(false)
  })

  it('throws when used outside provider', () => {
    expect(() => {
      renderHook(() => useDashboardFilters())
    }).toThrow('useDashboardFilters must be used within a <DashboardFilterProvider>')
  })
})
