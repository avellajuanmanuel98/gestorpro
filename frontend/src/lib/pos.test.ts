import { describe, expect, it, vi } from 'vitest'
import { cartTotals, newClientId, quickCashOptions, stepQuantity, toCents, type CartLine } from './pos'

const line = (over: Partial<CartLine>): CartLine => ({
  itemId: 1, name: 'x', unit: 'und', unitSymbol: 'und', price: '2000.00', taxRate: '0', quantity: '1', ...over,
})

describe('POS: vista previa', () => {
  it('calcula como el servidor (mismo ejemplo que el test del backend)', () => {
    const t = cartTotals([line({ quantity: '3' }), line({ price: '3000.00', taxRate: '19', quantity: '2' })])
    expect(t).toMatchObject({ subtotal: 1200000, tax: 114000, total: 1314000 })
  })

  it('el descuento no supera el total', () => {
    expect(cartTotals([line({})], '5000').total).toBe(0)
  })

  it('evita errores de float con decimales', () => {
    expect(cartTotals([line({ price: '26000.00', unit: 'kg', quantity: '0.25' })]).total).toBe(650000)
    expect(toCents('0.1') + toCents('0.2')).toBe(30)
  })

  it('sugiere billetes para pagar en efectivo', () => {
    expect(quickCashOptions(toCents('13140'))).toEqual([1314000, 1400000, 1500000, 2000000, 5000000])
  })

  it('las unidades suben de 1 en 1 y el peso de 0,25 en 0,25', () => {
    expect(stepQuantity(line({ quantity: '2' }), 1)).toBe('3')
    expect(stepQuantity(line({ unit: 'kg', quantity: '0.5' }), -1)).toBe('0.25')
  })
})

describe('newClientId', () => {
  const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

  it('genera UUID v4 únicos aunque no haya randomUUID (HTTP en la red local)', () => {
    const real = globalThis.crypto
    vi.stubGlobal('crypto', { getRandomValues: (a: Uint8Array<ArrayBuffer>) => real.getRandomValues(a) })
    const ids = new Set(Array.from({ length: 200 }, () => newClientId()))
    vi.unstubAllGlobals()
    expect(ids.size).toBe(200)
    for (const id of ids) expect(id).toMatch(UUID_V4)
  })
})
