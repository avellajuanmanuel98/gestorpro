import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('ticket térmico', () => {
  it('cabe en el ancho que imprime una impresora de 80 mm (72 mm útiles)', () => {
    const css = readFileSync(new URL('../index.css', import.meta.url), 'utf8')
    const width = css.match(/\.print-ticket\s*\{[^}]*width:\s*([\d.]+)mm/)
    expect(width).not.toBeNull()
    expect(Number(width![1])).toBeLessThanOrEqual(72)
  })
})
