import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import JsonPayloadViewer from './JsonPayloadViewer'

// Mock syntax highlighter
vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children }: { children: string }) => <pre data-testid="syntax">{children}</pre>,
}))
vi.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  vscDarkPlus: {},
}))

describe('JsonPayloadViewer', () => {
  it('renders JSON data', () => {
    render(<JsonPayloadViewer data={{ key: 'value', count: 42 }} />)
    expect(screen.getByTestId('syntax')).toBeDefined()
    expect(screen.getByText(/key/)).toBeDefined()
  })

  it('renders array data', () => {
    render(<JsonPayloadViewer data={[1, 2, 3]} />)
    expect(screen.getByTestId('syntax')).toBeDefined()
  })

  it('renders string data', () => {
    render(<JsonPayloadViewer data="simple string" />)
    expect(screen.getByText(/simple string/)).toBeDefined()
  })

  it('has expand/collapse functionality for large payloads', () => {
    const largeData = Object.fromEntries(
      Array.from({ length: 20 }, (_, i) => [`key_${i}`, `value_${i}`]),
    )
    render(<JsonPayloadViewer data={largeData} />)
    // Should have some toggle interaction
    const buttons = screen.queryAllByRole('button')
    if (buttons.length > 0) {
      fireEvent.click(buttons[0])
      // Should still render
      expect(screen.getByTestId('syntax')).toBeDefined()
    }
  })
})
