import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { useDashboardStore } from '../stores/dashboardStore'

vi.mock('react-resizable-panels', () => ({
  Panel: ({ children }: { children: React.ReactNode }) => <div data-testid="panel">{children}</div>,
  PanelGroup: ({ children }: { children: React.ReactNode }) => <div data-testid="panel-group">{children}</div>,
  PanelResizeHandle: () => <div data-testid="resize-handle" />,
}))

vi.mock('../components/investigation/InvestigationRail', () => ({
  default: () => <div data-testid="investigation-rail">Rail</div>,
}))

vi.mock('../components/chat/ChatPanel', () => ({
  default: () => <div data-testid="chat-panel">Chat</div>,
}))

vi.mock('../components/investigation/DashboardPanel', () => ({
  default: () => <div data-testid="dashboard-panel">Dashboard</div>,
}))

vi.mock('../components/investigation/ConversationAppBar', () => ({
  default: () => <div data-testid="app-bar">AppBar</div>,
}))

import InvestigationLayout from './InvestigationLayout'

describe('InvestigationLayout', () => {
  beforeEach(() => {
    useDashboardStore.setState({ isOpen: true })
  })

  it('renders all 3 panels', () => {
    const { getByTestId } = render(<InvestigationLayout />)
    expect(getByTestId('investigation-rail')).toBeDefined()
    expect(getByTestId('chat-panel')).toBeDefined()
    expect(getByTestId('dashboard-panel')).toBeDefined()
  })

  it('renders the app bar', () => {
    const { getByTestId } = render(<InvestigationLayout />)
    expect(getByTestId('app-bar')).toBeDefined()
  })

  it('renders panel group container', () => {
    const { getByTestId } = render(<InvestigationLayout />)
    expect(getByTestId('panel-group')).toBeDefined()
  })
})
