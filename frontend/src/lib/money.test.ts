import { describe, expect, it } from 'vitest'
import { formatCOP, toDisplayNumber } from './money'

const plain = (s: string) => s.replace(/\s/g, ' ')

describe('Dinero en pantalla', () => {
  it('pesos colombianos sin decimales y con punto de miles', () => {
    expect(plain(formatCOP('1234567.00'))).toBe('$ 1.234.567')
    expect(plain(formatCOP(6000))).toBe('$ 6.000')
  })

  it('abrevia solo desde un millón, y solo si se pide', () => {
    expect(plain(formatCOP('950000', { compact: true }))).toBe('$ 950.000')
    expect(formatCOP('2500000', { compact: true })).not.toContain('2.500.000')
  })

  it('un valor vacío o inválido se muestra como cero, nunca como NaN', () => {
    for (const v of [null, undefined, '', 'abc']) {
      expect(toDisplayNumber(v)).toBe(0)
      expect(formatCOP(v)).not.toContain('NaN')
    }
  })
})
