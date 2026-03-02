import { describe, it, expect, vi } from 'vitest'
import { parseAnsi } from './ansiParser'

vi.mock('anser', () => ({
  default: {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    ansiToHtml: (text: string, _opts: unknown) => {
      // Simple mock: wrap bold in <b>, red in <span style="color:red">
      const ESC = String.fromCharCode(0x1b)
      return text
        .replace(new RegExp(`${ESC}\\[1m(.*?)${ESC}\\[0m`, 'g'), '<b>$1</b>')
        .replace(new RegExp(`${ESC}\\[31m(.*?)${ESC}\\[0m`, 'g'), '<span style="color:red">$1</span>')
        .replace(new RegExp(`${ESC}\\[\\d+m`, 'g'), '')
    },
  },
}))

describe('parseAnsi', () => {
  it('returns plain text unchanged', () => {
    expect(parseAnsi('Hello, world!')).toBe('Hello, world!')
  })

  it('converts bold ANSI codes to HTML', () => {
    const result = parseAnsi('\x1b[1mBold text\x1b[0m')
    expect(result).toContain('<b>Bold text</b>')
  })

  it('converts red color ANSI codes', () => {
    const result = parseAnsi('\x1b[31mError message\x1b[0m')
    expect(result).toContain('Error message')
    expect(result).toContain('color:red')
  })

  it('strips unknown ANSI codes', () => {
    const result = parseAnsi('\x1b[42mGreen bg\x1b[0m')
    expect(result).toContain('Green bg')
    expect(result).not.toContain('\x1b')
  })

  it('handles empty string', () => {
    expect(parseAnsi('')).toBe('')
  })
})
