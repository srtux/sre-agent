import { render } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import TrajectorySankey from './TrajectorySankey'

import type { SankeyResponse } from '../types'

vi.mock('axios')

const mockData: SankeyResponse = { nodes: [], links: [] };

describe('TrajectorySankey', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <TrajectorySankey
        data={mockData}
        onNodeClick={vi.fn()}
        onEdgeClick={vi.fn()}
      />
    )
    expect(container).toBeInTheDocument()
  })
})
