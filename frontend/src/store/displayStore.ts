import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * Preferencias de pantalla de ESTE computador (no de la cuenta): pensadas para
 * que una persona mayor use GestorPro con comodidad.
 *
 * - Tamaño de letra: escala la raíz del documento. Todo lo que mide en rem
 *   (textos, botones, campos, espacios) crece parejo, sin desarmar el diseño.
 * - Modo fácil: menú corto con lo de todos los días y botones con palabras.
 * - Al cobrar: nada automático, solo abrir el cajón (imprime una línea mínima, porque el cajón
 *   se abre cuando la impresora imprime) o ticket y cajón. El cajón va conectado a la impresora,
 *   con "abrir cajón al imprimir" activo en su driver.
 * - Sonido de monedas: suena al cobrar y al abrir el cajón.
 */
export type TextSize = 'normal' | 'grande' | 'muy-grande'

export const TEXT_SIZES: { id: TextSize; label: string; scale: string }[] = [
  { id: 'normal', label: 'Normal', scale: '100%' },
  { id: 'grande', label: 'Grande', scale: '115%' },
  { id: 'muy-grande', label: 'Muy grande', scale: '130%' },
]

export type SaleAction = 'manual' | 'drawer' | 'ticket'

export const SALE_ACTIONS: { id: SaleAction; label: string }[] = [
  { id: 'manual', label: 'Al cobrar: nada automático' },
  { id: 'drawer', label: 'Al cobrar: solo abrir cajón' },
  { id: 'ticket', label: 'Al cobrar: ticket y cajón' },
]

export function applyTextSize(size: TextSize) {
  const option = TEXT_SIZES.find((t) => t.id === size) ?? TEXT_SIZES[0]
  document.documentElement.style.fontSize = option.scale
}

interface DisplayState {
  textSize: TextSize
  easyMode: boolean
  saleAction: SaleAction
  coinSound: boolean
  setTextSize: (size: TextSize) => void
  nextTextSize: () => void
  setEasyMode: (on: boolean) => void
  nextSaleAction: () => void
  setCoinSound: (on: boolean) => void
}

export const useDisplayStore = create<DisplayState>()(
  persist(
    (set, get) => ({
      textSize: 'normal',
      easyMode: false,
      saleAction: 'manual',
      coinSound: true,
      setTextSize: (textSize) => {
        applyTextSize(textSize)
        set({ textSize })
      },
      nextTextSize: () => {
        const i = TEXT_SIZES.findIndex((t) => t.id === get().textSize)
        get().setTextSize(TEXT_SIZES[(i + 1) % TEXT_SIZES.length].id)
      },
      setEasyMode: (easyMode) => set({ easyMode }),
      nextSaleAction: () => {
        const i = SALE_ACTIONS.findIndex((a) => a.id === get().saleAction)
        set({ saleAction: SALE_ACTIONS[(i + 1) % SALE_ACTIONS.length].id })
      },
      setCoinSound: (coinSound) => set({ coinSound }),
    }),
    {
      name: 'gestorpro-display',
      version: 1,
      // v0 tenía "autoPrint" (sí/no): sí equivale a "ticket y cajón"
      migrate: (old, version) => {
        const state = (old ?? {}) as Record<string, unknown>
        if (version < 1) {
          state.saleAction = state.autoPrint ? 'ticket' : 'manual'
          delete state.autoPrint
        }
        return state as unknown as DisplayState
      },
      onRehydrateStorage: () => (state) => {
        if (state?.textSize) applyTextSize(state.textSize)
      },
    },
  ),
)
