/**
 * Project selection store (Zustand).
 * Ported from autosre/lib/services/project_service.dart
 */
import { create } from 'zustand'

interface ProjectState {
  projectId: string
  recentProjects: string[]
  starredProjects: string[]

  setProjectId: (id: string) => void
  addRecentProject: (id: string) => void
  toggleStarred: (id: string) => void
}

const MAX_RECENT = 10
const STORAGE_KEY_RECENT = 'sre_recent_projects'
const STORAGE_KEY_STARRED = 'sre_starred_projects'

function loadFromStorage(key: string): string[] {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export const useProjectStore = create<ProjectState>((set) => ({
  projectId:
    new URLSearchParams(window.location.search).get('project_id') ||
    localStorage.getItem('agent_graph_project_id') ||
    '',
  recentProjects: loadFromStorage(STORAGE_KEY_RECENT),
  starredProjects: loadFromStorage(STORAGE_KEY_STARRED),

  setProjectId: (id) => {
    localStorage.setItem('agent_graph_project_id', id)
    set((state) => {
      const recent = [id, ...state.recentProjects.filter((p) => p !== id)].slice(
        0,
        MAX_RECENT,
      )
      localStorage.setItem(STORAGE_KEY_RECENT, JSON.stringify(recent))
      return { projectId: id, recentProjects: recent }
    })
  },

  addRecentProject: (id) =>
    set((state) => {
      const recent = [id, ...state.recentProjects.filter((p) => p !== id)].slice(
        0,
        MAX_RECENT,
      )
      localStorage.setItem(STORAGE_KEY_RECENT, JSON.stringify(recent))
      return { recentProjects: recent }
    }),

  toggleStarred: (id) =>
    set((state) => {
      const starred = state.starredProjects.includes(id)
        ? state.starredProjects.filter((p) => p !== id)
        : [...state.starredProjects, id]
      localStorage.setItem(STORAGE_KEY_STARRED, JSON.stringify(starred))
      return { starredProjects: starred }
    }),
}))
