/**
 * Prompt history hook backed by localStorage.
 * Stores up to 50 most recent prompts.
 * Supports Up/Down navigation through history.
 */
import { useRef, useCallback } from 'react'

const STORAGE_KEY = 'sre_prompt_history'
const MAX_ENTRIES = 50

function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveHistory(items: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(-MAX_ENTRIES)))
  } catch {
    // localStorage full or unavailable
  }
}

export function usePromptHistory() {
  const indexRef = useRef(-1)

  const add = useCallback((prompt: string) => {
    const history = loadHistory()
    // Avoid duplicate of last entry
    if (history[history.length - 1] !== prompt) {
      history.push(prompt)
      saveHistory(history)
    }
    indexRef.current = -1
  }, [])

  const navigateUp = useCallback((): string | null => {
    const history = loadHistory()
    if (history.length === 0) return null

    if (indexRef.current === -1) {
      indexRef.current = history.length - 1
    } else if (indexRef.current > 0) {
      indexRef.current--
    }
    return history[indexRef.current] ?? null
  }, [])

  const navigateDown = useCallback((): string | null => {
    const history = loadHistory()
    if (indexRef.current === -1) return null

    if (indexRef.current < history.length - 1) {
      indexRef.current++
      return history[indexRef.current] ?? null
    }

    // Past the end — reset
    indexRef.current = -1
    return null
  }, [])

  return { add, navigateUp, navigateDown }
}
