import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { renderHook } from '@testing-library/react'
import { ToastContainer, useToast } from './StatusToast'

describe('StatusToast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('ToastContainer renders nothing with no toasts', () => {
    const { container } = render(<ToastContainer />)
    expect(container.children.length).toBe(0)
  })

  it('useToast returns show function', () => {
    const { result } = renderHook(() => useToast())
    expect(typeof result.current.show).toBe('function')
  })

  it('shows toast when useToast.show is called', () => {
    const HarnessInner = () => {
      const { show } = useToast()
      return <button onClick={() => show('Test message', 'success')}>Trigger</button>
    }
    render(
      <>
        <HarnessInner />
        <ToastContainer />
      </>
    )
    fireEvent.click(screen.getByText('Trigger'))
    expect(screen.getByText('Test message')).toBeDefined()
  })

  it('shows correct icon for error type', () => {
    const HarnessInner = () => {
      const { show } = useToast()
      return <button onClick={() => show('Error msg', 'error')}>Trigger</button>
    }
    render(
      <>
        <HarnessInner />
        <ToastContainer />
      </>
    )
    fireEvent.click(screen.getByText('Trigger'))
    expect(screen.getByText('Error msg')).toBeDefined()
    // Error icon is ✗
    expect(screen.getByText('\u2717')).toBeDefined()
  })

  it('dismiss button removes toast', () => {
    const HarnessInner = () => {
      const { show } = useToast()
      return <button onClick={() => show('Dismiss me', 'info')}>Trigger</button>
    }
    render(
      <>
        <HarnessInner />
        <ToastContainer />
      </>
    )
    fireEvent.click(screen.getByText('Trigger'))
    expect(screen.getByText('Dismiss me')).toBeDefined()
    fireEvent.click(screen.getByLabelText('Dismiss'))
    expect(screen.queryByText('Dismiss me')).toBeNull()
  })

  it('auto-dismisses after 5 seconds', () => {
    const HarnessInner = () => {
      const { show } = useToast()
      return <button onClick={() => show('Vanishing toast', 'warning')}>Trigger</button>
    }
    render(
      <>
        <HarnessInner />
        <ToastContainer />
      </>
    )
    fireEvent.click(screen.getByText('Trigger'))
    expect(screen.getByText('Vanishing toast')).toBeDefined()

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(screen.queryByText('Vanishing toast')).toBeNull()
  })
})
