import { create } from 'zustand'
import type { POSItem } from '@/api/pos'
import type { CartLine } from '@/lib/pos'
import { isWholeUnit } from '@/lib/pos'

interface CartState {
  lines: CartLine[]
  customer: { id: number; label: string } | null
  add: (item: POSItem, quantity?: number) => void
  setQuantity: (itemId: number, quantity: string) => void
  remove: (itemId: number) => void
  setCustomer: (customer: CartState['customer']) => void
  clear: () => void
}

/** Carrito del POS (en memoria). Los precios guardados aquí son solo para la vista previa. */
export const useCartStore = create<CartState>((set) => ({
  lines: [],
  customer: null,
  add: (item, quantity) => set((s) => {
    const step = quantity ?? (isWholeUnit(item.unit) ? 1 : 0.5)
    const existing = s.lines.find((l) => l.itemId === item.id)
    if (existing) {
      return { lines: s.lines.map((l) => (l.itemId === item.id
        ? { ...l, quantity: String(Math.round((Number(l.quantity) + step) * 1000) / 1000) } : l)) }
    }
    return { lines: [...s.lines, { itemId: item.id, name: item.name, unit: item.unit, unitSymbol: item.unit_symbol,
                                   price: item.price, taxRate: item.tax_rate, quantity: String(step) }] }
  }),
  setQuantity: (itemId, quantity) => set((s) => ({
    lines: Number(quantity) > 0 || quantity === ''
      ? s.lines.map((l) => (l.itemId === itemId ? { ...l, quantity } : l))
      : s.lines.filter((l) => l.itemId !== itemId),
  })),
  remove: (itemId) => set((s) => ({ lines: s.lines.filter((l) => l.itemId !== itemId) })),
  setCustomer: (customer) => set({ customer }),
  clear: () => set({ lines: [], customer: null }),
}))
