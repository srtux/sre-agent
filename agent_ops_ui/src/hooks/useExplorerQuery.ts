/**
 * Query execution hook for the explorer.
 * Manages loading, results, and error state.
 */
import { useState, useCallback } from 'react'
import { executeQuery, type QueryResult } from '../api/explorer'

const HISTORY_KEY = 'sre_query_history'
const MAX_HISTORY = 20

export interface QueryHistoryEntry {
  query: string
  language: string
  timestamp: string
}

function loadHistory(): QueryHistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch {
    return []
  }
}

function saveToHistory(query: string, language: string): void {
  const history = loadHistory()
  history.unshift({ query, language, timestamp: new Date().toISOString() })
  // Deduplicate by query+language, keep max entries
  const seen = new Set<string>()
  const deduped = history.filter((entry) => {
    const key = `${entry.language}:${entry.query}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
  localStorage.setItem(HISTORY_KEY, JSON.stringify(deduped.slice(0, MAX_HISTORY)))
}

export function useExplorerQuery() {
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState<QueryResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const execute = useCallback(async (query: string, language: string) => {
    if (!query.trim()) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await executeQuery(query, language)
      setResults(data)
      saveToHistory(query, language)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Query execution failed'
      setError(message)
      setResults(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const clearResults = useCallback(() => {
    setResults(null)
    setError(null)
  }, [])

  return { execute, isLoading, results, error, clearResults }
}
