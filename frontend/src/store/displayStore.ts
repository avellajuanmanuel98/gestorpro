import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * Preferencias de pantalla de ESTE computador (no de la cuenta): pensadas para
 * que una persona mayor use GestorPro con comodidad.
 *
 * - Tamaño de letra: escala la raíz del documento. Todo lo que mide en rem
 *   (textos, botones, campos, espacios) crece parejo, sin desarmar el diseño.
 * - Modo fácil: menú corto con lo de todos los días y botones con palabras.
 * - Ticket automático: al cobrar se imprime el ticket sin pedir clic. Con el cajón monedero
 *   conectado a la impresora (y "abrir cajón al imprimir" en su driver), cobrar abre el cajón.
 * - Sonido de monedas: suena al cobrar y al abrir el cajón.
 */
export type TextSize = 'normal' | 'grande' | 'muy-grande'

export const TEXT_SIZES: { id: TextSize; label: string; scale: string }[] = [
  { id: 'normal', label: 'Normal', scale: '100%' },
  { id: 'grande', label: 'Grande', scale: '115%' },
  { id: 'muy-grande', label: 'Muy grande', scale: '130%' },
]

export function applyTextSize(size: TextSize) {
  const option = TEXT_SIZES.find((t) => t.id === size) ?? TEXT_SIZES[0]
  document.documentElement.style.fontSize = option.scale
}

interface DisplayState {
  textSize: TextSize
  easyMode: boolean
  autoPrint: boolean
  coinSound: boolean
  setTextSize: (size: TextSize) => void
  nextTextSize: () => void
  setEasyMode: (on: boolean) => void
  setAutoPrint: (on: boolean) => void
  setCoinSound: (on: boolean) => void
}

export const useDisplayStore = create<DisplayState>()(
  persist(
    (set, get) => ({
      textSize: 'normal',
      easyMode: false,
      autoPrint: false,
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
      setAutoPrint: (autoPrint) => set({ autoPrint }),
      setCoinSound: (coinSound) => set({ coinSound }),
    }),
    {
      name: 'gestorpro-display',
      onRehydrateStorage: () => (state) => {
        if (state?.textSize) applyTextSize(state.textSize)
      },
    },
  ),
)
