/**
 * Left sidebar session list panel.
 */
import React, { useState } from 'react'
import { useSessionStore, type Session } from '../../stores/sessionStore'
import {
  useSessions,
  useCreateSession,
  useDeleteSession,
  useRenameSession,
} from '../../hooks/useSessions'
import { colors, typography, spacing, radii, transitions } from '../../theme/tokens'
import { glassCard, glassButton, glassInput } from '../../theme/glassStyles'

export const SessionPanel: React.FC = () => {
  const currentSessionId = useSessionStore((s) => s.currentSessionId)
  const setCurrentSession = useSessionStore((s) => s.setCurrentSession)
  const { data: sessions, isLoading } = useSessions()
  const createMutation = useCreateSession()
  const deleteMutation = useDeleteSession()
  const renameMutation = useRenameSession()

  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  const handleCreate = () => createMutation.mutate()

  const handleDelete = (id: string) => {
    if (window.confirm('Delete this session?')) {
      deleteMutation.mutate(id)
    }
  }

  const startRename = (session: Session) => {
    setRenamingId(session.id)
    setRenameValue(session.title)
  }

  const submitRename = () => {
    if (renamingId && renameValue.trim()) {
      renameMutation.mutate({ sessionId: renamingId, title: renameValue.trim() })
    }
    setRenamingId(null)
  }

  return (
    <div style={styles.panel}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.headerTitle}>Sessions</span>
        <button
          style={styles.addButton}
          onClick={handleCreate}
          disabled={createMutation.isPending}
          title="New Session"
          onMouseEnter={(e) => {
            e.currentTarget.style.background = colors.glassHover
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent'
          }}
        >
          +
        </button>
      </div>

      {/* List */}
      <div style={styles.list}>
        {isLoading && <p style={styles.placeholder}>Loading sessions...</p>}
        {!isLoading && (!sessions || sessions.length === 0) && (
          <p style={styles.placeholder}>No sessions yet</p>
        )}
        {sessions?.map((session) => {
          const isActive = session.id === currentSessionId
          return (
            <div
              key={session.id}
              style={{
                ...styles.item,
                ...(isActive ? styles.itemActive : {}),
              }}
              onClick={() => setCurrentSession(session.id)}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.background = colors.cardHover
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = 'transparent'
              }}
            >
              {renamingId === session.id ? (
                <input
                  style={styles.renameInput}
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={submitRename}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') submitRename()
                    if (e.key === 'Escape') setRenamingId(null)
                  }}
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <span style={styles.itemTitle}>{session.title}</span>
              )}
              <div style={styles.actions}>
                <button
                  style={styles.iconBtn}
                  onClick={(e) => {
                    e.stopPropagation()
                    startRename(session)
                  }}
                  title="Rename"
                >
                  &#9998;
                </button>
                <button
                  style={styles.iconBtn}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(session.id)
                  }}
                  title="Delete"
                >
                  &#128465;
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    ...glassCard(),
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: `${spacing.md}px ${spacing.lg}px`,
    borderBottom: `1px solid ${colors.surfaceBorder}`,
  },
  headerTitle: {
    color: colors.textPrimary,
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    fontFamily: typography.fontFamily,
  },
  addButton: {
    ...glassButton(),
    width: 28,
    height: 28,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: typography.sizes.lg,
    padding: 0,
    background: 'transparent',
    border: 'none',
    color: colors.cyan,
    fontFamily: typography.fontFamily,
  },
  list: {
    flex: 1,
    overflowY: 'auto',
    padding: spacing.sm,
  },
  placeholder: {
    color: colors.textMuted,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    textAlign: 'center',
    padding: spacing.lg,
    margin: 0,
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: `${spacing.sm}px ${spacing.md}px`,
    borderRadius: radii.md,
    cursor: 'pointer',
    transition: transitions.fast,
    gap: spacing.sm,
  },
  itemActive: {
    background: `${colors.cyan}15`,
    border: `1px solid ${colors.cyan}40`,
  },
  itemTitle: {
    color: colors.textPrimary,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flex: 1,
  },
  actions: {
    display: 'flex',
    gap: 2,
    flexShrink: 0,
  },
  iconBtn: {
    background: 'transparent',
    border: 'none',
    color: colors.textMuted,
    cursor: 'pointer',
    fontSize: '14px',
    padding: 4,
    borderRadius: radii.sm,
    lineHeight: 1,
    transition: transitions.fast,
  },
  renameInput: {
    ...glassInput(),
    flex: 1,
    padding: `${spacing.xs}px ${spacing.sm}px`,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
  },
}
