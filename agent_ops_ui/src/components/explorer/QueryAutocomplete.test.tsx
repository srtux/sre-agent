import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import QueryAutocomplete from './QueryAutocomplete'

describe('QueryAutocomplete', () => {
  const onSelect = vi.fn()

  it('renders nothing when not visible', () => {
    const { container } = render(
      <QueryAutocomplete query="" language="SQL" onSelect={onSelect} visible={false} />
    )
    expect(container.children).toHaveLength(0)
  })

  it('renders keyword suggestions when visible', () => {
    render(
      <QueryAutocomplete query="SEL" language="SQL" onSelect={onSelect} visible={true} />
    )
    expect(screen.getByText('SELECT')).toBeDefined()
  })

  it('calls onSelect when keyword mousedown fires', () => {
    render(
      <QueryAutocomplete query="SEL" language="SQL" onSelect={onSelect} visible={true} />
    )
    fireEvent.mouseDown(screen.getByText('SELECT'))
    expect(onSelect).toHaveBeenCalledWith('SELECT')
  })

  it('filters keywords based on query input', () => {
    render(
      <QueryAutocomplete query="WH" language="SQL" onSelect={onSelect} visible={true} />
    )
    expect(screen.getByText('WHERE')).toBeDefined()
  })
})
