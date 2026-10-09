import { describe, expect, it } from 'vitest'
import { formatQty, formatUnitCost, previewMargin } from './catalog'

describe('catálogo', () => {
  it('formatea cantidades con su unidad', () => {
    expect(formatQty('12.5000', 'kg')).toBe('12,5 kg')
    expect(formatQty('180.0000', 'und')).toBe('180 und')
  })

  it('conserva decimales en costos unitarios pequeños', () => {
    expect(formatUnitCost('3.2')).toMatch(/3,2/)
    expect(formatUnitCost('3200.0000')).toMatch(/3\.200/)
  })

  it('calcula el margen de vista previa y lo omite sin datos', () => {
    expect(previewMargin('1500', '500')).toBe(66.7)
    expect(previewMargin('1500', '')).toBeNull()
    expect(previewMargin('0', '500')).toBeNull()
  })
})
