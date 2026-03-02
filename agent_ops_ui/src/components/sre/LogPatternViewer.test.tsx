import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import LogPatternViewer from './LogPatternViewer'
import { mockLogPatterns } from '../../test-utils/mockData'

describe('LogPatternViewer', () => {
  it('renders pattern templates', () => {
    // The component prop is named "patterns", not "data"
    render(<LogPatternViewer patterns={mockLogPatterns} />)
    expect(screen.getByText(/Connection refused/)).toBeDefined()
    expect(screen.getByText(/High memory/)).toBeDefined()
  })

  it('shows pattern counts', () => {
    render(<LogPatternViewer patterns={mockLogPatterns} />)
    expect(screen.getByText('42')).toBeDefined()
    expect(screen.getByText('1200')).toBeDefined()
  })
})
