/**
 * Formato de dinero único para toda la app.
 *
 * El backend envía importes como string decimal exacto ("1469.11"). Aquí solo
 * se formatean para mostrar; ningún cálculo monetario que importe se hace en
 * el navegador (los totales los calcula el servidor).
 */
const full = new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 0,
})
const compact = new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP', notation: 'compact', maximumFractionDigits: 1,
})
const compactNumber = new Intl.NumberFormat('es-CO', { notation: 'compact', maximumFractionDigits: 1 })

export type MoneyValue = string | number | null | undefined

/** Conversión SOLO para presentación (gráficos, formato). */
export function toDisplayNumber(value: MoneyValue): number {
  const n = typeof value === 'number' ? value : Number(value ?? 0)
  return Number.isFinite(n) ? n : 0
}

export function formatCOP(value: MoneyValue, options: { compact?: boolean } = {}): string {
  const n = toDisplayNumber(value)
  return options.compact && Math.abs(n) >= 1_000_000 ? compact.format(n) : full.format(n)
}

export function formatCompactNumber(value: MoneyValue): string {
  return compactNumber.format(toDisplayNumber(value))
}
