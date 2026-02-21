import { render } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import TrajectorySankey from './TrajectorySankey'
import React from 'react'

vi.mock('axios')

const mockFilters = {
  projectId: 'test-project',
  hours: 24,
  errorsOnly: false,
  traceDataset: 'traces',
  serviceName: 'agent-A',
}

describe('TrajectorySankey', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <TrajectorySankey
        filters={mockFilters}
        activeTab="sankey"
        onNodeSelect={vi.fn()}
        onEdgeSelect={vi.fn()}
        triggerLoad={0}
        onLoadComplete={vi.fn()}
        autoRefresh={{ enabled: false, intervalSeconds: 60 }}
      />
    )
    expect(container).toBeInTheDocument()
  })
})
