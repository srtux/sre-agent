/**
 * 3-panel resizable layout: Investigation Rail + Chat Panel + Dashboard Panel.
 * Ported from autosre/lib/pages/conversation_page.dart
 */
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { colors, radii } from '../theme/tokens'
import InvestigationRail from '../components/investigation/InvestigationRail'
import ChatPanel from '../components/chat/ChatPanel'
import DashboardPanel from '../components/investigation/DashboardPanel'
import ConversationAppBar from '../components/investigation/ConversationAppBar'
import { useDashboardStore } from '../stores/dashboardStore'

const resizeHandleStyle: React.CSSProperties = {
  width: 4,
  background: colors.surfaceBorder,
  cursor: 'col-resize',
  transition: 'background 0.15s ease',
}

export default function InvestigationLayout() {
  const isOpen = useDashboardStore((s) => s.isOpen)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
      <ConversationAppBar />
      <PanelGroup direction="horizontal" style={{ flex: 1 }}>
        {/* Investigation Rail */}
        <Panel defaultSize={4} minSize={3} maxSize={15}>
          <InvestigationRail />
        </Panel>
        <PanelResizeHandle style={resizeHandleStyle} />

        {/* Chat Panel */}
        <Panel defaultSize={isOpen ? 50 : 96} minSize={30}>
          <ChatPanel />
        </Panel>

        {/* Dashboard Panel — shown when data arrives */}
        {isOpen && (
          <>
            <PanelResizeHandle style={resizeHandleStyle} />
            <Panel
              defaultSize={46}
              minSize={20}
              style={{
                background: colors.background,
                borderLeft: `1px solid ${colors.surfaceBorder}`,
                borderRadius: `${radii.lg}px 0 0 ${radii.lg}px`,
              }}
            >
              <DashboardPanel />
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  )
}
