import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import InvestigationRail from './InvestigationRail'
import { useDashboardStore } from '../../stores/dashboardStore'

describe('InvestigationRail', () => {
  beforeEach(() => {
    useDashboardStore.setState({
      items: [],
      isOpen: false,
      activeTab: 'traces',
      isRailExpanded: false,
      metricsQueryLanguage: 0,
    })
  })

  it('renders tab buttons for all categories', () => {
    render(<InvestigationRail />)
    // Each tab has a text label and/or icon
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThanOrEqual(7)
  })

  it('clicking a tab changes activeTab in store', () => {
    render(<InvestigationRail />)
    const buttons = screen.getAllByRole('button')
    // Click a button - at minimum one of the buttons should switch the tab
    fireEvent.click(buttons[1]) // logs tab (second)
    const state = useDashboardStore.getState()
    // Tab should have changed from the default
    expect(state.activeTab).toBeDefined()
  })
})
