import type { ItemKind } from '@/types'
import { toDisplayNumber, type MoneyValue } from './money'

export const ITEM_KIND_LABEL: Record<ItemKind, string> = {
  finished_good: 'Elaborado',
  resale: 'Reventa',
  service: 'Servicio',
  raw_material: 'Ingrediente',
}

/** Tipos que se crean desde la pantalla de Productos. */
export const PRODUCT_KIND_OPTIONS: { value: ItemKind; label: string; hint: string }[] = [
  { value: 'finished_good', label: 'Elaborado', hint: 'Lo produces tú: panes, tortas, bebidas preparadas' },
  { value: 'resale', label: 'Reventa', hint: 'Lo compras listo y lo revendes: gaseosas, agua, leche' },
  { value: 'service', label: 'Servicio', hint: 'No tiene existencias: domicilio, decoración' },
]

const qtyFormat = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 3 })

/** "12,5 kg", "180 und". Solo presentación: la cantidad exacta viene del servidor. */
export function formatQty(value: MoneyValue, symbol?: string): string {
  const text = qtyFormat.format(toDisplayNumber(value))
  return symbol ? `${text} ${symbol}` : text
}

const unitCostFormat = new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 2,
})

/** Costo por unidad: conserva decimales para unidades pequeñas ($ 3,2 por g). */
export function formatUnitCost(value: MoneyValue): string {
  return unitCostFormat.format(toDisplayNumber(value))
}

/** Vista previa del margen al escribir precio y costo. El valor oficial lo calcula el servidor. */
export function previewMargin(price: string, cost: string): number | null {
  const p = Number(price), c = Number(cost)
  if (!Number.isFinite(p) || !Number.isFinite(c) || p <= 0 || c <= 0) return null
  return Math.round(((p - c) / p) * 1000) / 10
}
