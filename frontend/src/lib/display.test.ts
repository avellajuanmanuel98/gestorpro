import { beforeEach, describe, expect, it } from 'vitest'
import { TEXT_SIZES, applyTextSize, useDisplayStore } from '@/store/displayStore'

// Los tests corren sin navegador: basta con la raíz del documento y su estilo
const root = { style: { fontSize: '' } }
Object.assign(globalThis, { document: { documentElement: root } })

describe('Pantalla: tamaño de letra y modo fácil', () => {
  beforeEach(() => {
    useDisplayStore.setState({ textSize: 'normal', easyMode: false })
    root.style.fontSize = ''
  })

  it('el tamaño de letra escala la raíz del documento, así crece toda la pantalla pareja', () => {
    applyTextSize('grande')
    expect(document.documentElement.style.fontSize).toBe('115%')
    applyTextSize('muy-grande')
    expect(document.documentElement.style.fontSize).toBe('130%')
  })

  it('el botón "Letra" recorre Normal → Grande → Muy grande → Normal', () => {
    const seen = [useDisplayStore.getState().textSize]
    for (let i = 0; i < TEXT_SIZES.length; i++) {
      useDisplayStore.getState().nextTextSize()
      seen.push(useDisplayStore.getState().textSize)
    }
    expect(seen).toEqual(['normal', 'grande', 'muy-grande', 'normal'])
    expect(document.documentElement.style.fontSize).toBe('100%')
  })

  it('el modo fácil se activa y se desactiva', () => {
    useDisplayStore.getState().setEasyMode(true)
    expect(useDisplayStore.getState().easyMode).toBe(true)
    useDisplayStore.getState().setEasyMode(false)
    expect(useDisplayStore.getState().easyMode).toBe(false)
  })
  it('"Al cobrar" recorre: nada automático → solo abrir cajón → ticket y cajón', () => {
    useDisplayStore.setState({ saleAction: 'manual' })
    const seen = [useDisplayStore.getState().saleAction]
    for (let i = 0; i < 3; i++) {
      useDisplayStore.getState().nextSaleAction()
      seen.push(useDisplayStore.getState().saleAction)
    }
    expect(seen).toEqual(['manual', 'drawer', 'ticket', 'manual'])
  })
})
