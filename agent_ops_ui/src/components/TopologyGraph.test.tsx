import { render } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import TopologyGraph from './TopologyGraph'
import React from 'react'
import { ReactFlowProvider } from '@xyflow/react'

vi.mock('axios')

const mockFilters = {
  projectId: 'test-project',
  hours: 24,
  errorsOnly: false,
  traceDataset: 'traces',
  serviceName: 'agent-A',
}

describe('TopologyGraph', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <ReactFlowProvider>
        <TopologyGraph
          filters={mockFilters}
          activeTab="topology"
          onNodeSelect={vi.fn()}
          onEdgeSelect={vi.fn()}
          triggerLoad={0}
          onLoadComplete={vi.fn()}
          autoRefresh={{ enabled: false, intervalSeconds: 60 }}
        />
      </ReactFlowProvider>
    )
    expect(container).toBeInTheDocument()
  })
})
