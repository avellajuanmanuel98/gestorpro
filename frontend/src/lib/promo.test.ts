import { describe, expect, it } from 'vitest'
import { receiptPromo } from './promo'

describe('publicidad al pie del ticket', () => {
  it('usa la marca del tipo de negocio y el WhatsApp de contacto', () => {
    expect(receiptPromo('bakery').system).toBe('Sistema Miga by GestorPro')
    expect(receiptPromo('generic').system).toBe('Sistema GestorPro')
    expect(receiptPromo().contact).toBe('WhatsApp 302 205 2551')
  })
})
