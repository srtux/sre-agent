import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ToolLogComponent from './ToolLogComponent'
import { mockToolLog } from '../../test-utils/mockData'

describe('ToolLogComponent', () => {
  it('renders tool name', () => {
    render(<ToolLogComponent data={mockToolLog} />)
    expect(screen.getByText('get_traces')).toBeDefined()
  })

  it('renders status icon', () => {
    render(<ToolLogComponent data={mockToolLog} />)
    // Status "completed" is shown as a checkmark emoji, not the word "completed"
    // Verify the status icon is present (checkmark: \u2705)
    expect(screen.getByText('\u2705')).toBeDefined()
  })

  it('renders duration', () => {
    render(<ToolLogComponent data={mockToolLog} />)
    // Duration 1250ms is formatted as "1.3s" by formatDuration (since >= 1000)
    expect(screen.getByText('1.3s')).toBeDefined()
  })
})
