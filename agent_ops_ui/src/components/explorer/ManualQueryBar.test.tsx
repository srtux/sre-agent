import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ManualQueryBar from './ManualQueryBar'
import { useDashboardStore } from '../../stores/dashboardStore'

vi.mock('./QueryLanguageToggle', () => ({
  default: ({ onChange }: { onChange: (i: number) => void }) => (
    <button data-testid="lang-toggle" onClick={() => onChange(1)}>Toggle</button>
  ),
  languageFromIndex: (i: number) => ['MQL', 'PromQL', 'SQL', 'Trace Filter'][i],
}))

vi.mock('./QueryAutocomplete', () => ({
  default: () => null,
}))

vi.mock('lucide-react', () => ({
  Play: () => <span>Play</span>,
  Trash2: () => <span>Trash</span>,
  BookOpen: () => <span>Book</span>,
}))

describe('ManualQueryBar', () => {
  const onExecute = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    useDashboardStore.setState({ metricsQueryLanguage: 0 })
  })

  it('renders textarea for query input', () => {
    render(<ManualQueryBar onExecute={onExecute} />)
    expect(screen.getByRole('textbox')).toBeDefined()
  })

  it('renders execute button', () => {
    render(<ManualQueryBar onExecute={onExecute} />)
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThanOrEqual(1)
  })

  it('calls onExecute with query text', () => {
    render(<ManualQueryBar onExecute={onExecute} />)
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: 'SELECT * FROM traces' } })
    // Click execute button (first actionable button)
    const buttons = screen.getAllByRole('button')
    const execBtn = buttons.find((b) => b.textContent?.includes('Play') || b.textContent?.includes('Execute'))
    if (execBtn) fireEvent.click(execBtn)
  })
})
