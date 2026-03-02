import anser from 'anser'

/**
 * Convert ANSI escape codes to HTML span tags with inline styles.
 * Supports bold, standard colors (30-37, 90-97), and reset.
 */
export function parseAnsi(text: string): string {
  return anser.ansiToHtml(text, { use_classes: false })
}
