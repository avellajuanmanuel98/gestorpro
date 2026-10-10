import type { ItemKind, Unit } from '@/types'
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


/** Unidades de la misma dimensión (masa, volumen o conteo) que la unidad del ítem. */
export function compatibleUnits(units: Unit[], itemUnit: string): Unit[] {
  const base = units.find((u) => u.code === itemUnit)
  return base ? units.filter((u) => u.dimension === base.dimension) : units
}

/** Conversión SOLO para vista previa; la oficial la hace el servidor (kernel/units). */
export function convertQty(value: number, from: string, to: string, units: Unit[]): number {
  const a = units.find((u) => u.code === from), b = units.find((u) => u.code === to)
  if (!a || !b || a.dimension !== b.dimension) return NaN
  return (value * Number(a.factor)) / Number(b.factor)
}

const MOVEMENT_TONE: Record<string, 'in' | 'out'> = {
  opening: 'in', purchase: 'in', sale_void: 'in', production_output: 'in', adjustment_in: 'in',
  sale: 'out', production_consume: 'out', waste: 'out', adjustment_out: 'out',
}
export const isInbound = (type: string) => MOVEMENT_TONE[type] === 'in'
