/**
 * Cálculos de VISTA PREVIA del POS. Se hacen en centavos enteros para no
 * arrastrar errores de float, con el mismo redondeo que el servidor (mitad
 * hacia arriba). El total que vale es el que devuelve el servidor al cobrar.
 */
export interface CartLine {
  itemId: number
  name: string
  unit: string
  unitSymbol: string
  price: string      // antes de IVA
  taxRate: string
  quantity: string
}

export const toCents = (value: string | number): number => Math.round(Number(value) * 100)
export const fromCents = (cents: number): string => (cents / 100).toFixed(2)

export function lineTotals(line: CartLine) {
  const subtotal = Math.round(Number(line.quantity) * toCents(line.price))
  const tax = Math.round((subtotal * Number(line.taxRate)) / 100)
  return { subtotal, tax, total: subtotal + tax }
}

export function cartTotals(lines: CartLine[], discount = '0') {
  const sums = lines.map(lineTotals).reduce(
    (acc, t) => ({ subtotal: acc.subtotal + t.subtotal, tax: acc.tax + t.tax }), { subtotal: 0, tax: 0 })
  const gross = sums.subtotal + sums.tax
  const discountCents = Math.min(Math.max(toCents(discount || 0), 0), gross)
  return { ...sums, discount: discountCents, total: gross - discountCents }
}

/** Billetes con los que el cliente probablemente pagará (sugerencias de efectivo). */
export function quickCashOptions(totalCents: number): number[] {
  const bills = [2000, 5000, 10000, 20000, 50000, 100000].map((b) => b * 100)
  const options = new Set<number>([totalCents])
  for (const bill of bills) {
    const rounded = Math.ceil(totalCents / bill) * bill
    if (rounded > totalCents) options.add(rounded)
  }
  return [...options].sort((a, b) => a - b).slice(0, 5)
}

/** Lo que se vende por unidad va en enteros; por peso o volumen admite decimales. */
export const isWholeUnit = (unit: string) => unit === 'und'

export function stepQuantity(line: CartLine, delta: number): string {
  const step = isWholeUnit(line.unit) ? 1 : 0.25
  const next = Math.max(0, Math.round((Number(line.quantity) + delta * step) * 1000) / 1000)
  return String(next)
}

/** Billetes y monedas de Colombia para el conteo del cierre. */
export const DENOMINATIONS = [100000, 50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50]

export const newClientId = (): string =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
      })
