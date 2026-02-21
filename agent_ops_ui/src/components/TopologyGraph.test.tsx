import { render } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import TopologyGraph from './TopologyGraph'
import { ReactFlowProvider } from '@xyflow/react'

vi.mock('axios')


describe('TopologyGraph', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <ReactFlowProvider>
        <TopologyGraph
          nodes={[]}
          edges={[]}
          onNodeClick={vi.fn()}
          onEdgeClick={vi.fn()}
        />
      </ReactFlowProvider>
    )
    expect(container).toBeInTheDocument()
  })
})
