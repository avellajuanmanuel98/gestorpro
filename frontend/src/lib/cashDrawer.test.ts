import { describe, expect, it } from 'vitest'
import { printThenRemove } from './cashDrawer'

function fakeWindow() {
  const listeners: Record<string, () => void> = {}
  const timers: (() => void)[] = []
  return {
    listeners, timers, printed: 0,
    print() { this.printed++ },
    addEventListener(name: string, fn: () => void) { listeners[name] = fn },
    setTimeout(fn: () => void) { timers.push(fn); return 0 },
  }
}

describe('ticket para abrir el cajón', () => {
  it('sigue en la página cuando Chrome imprime sin preguntar (después de window.print)', () => {
    const win = fakeWindow()
    let inPage = false
    const el = { remove: () => { inPage = false } }
    printThenRemove(el, { appendChild: () => { inPage = true } }, win as never)
    expect(win.printed).toBe(1)
    expect(inPage).toBe(true)   // antes se quitaba aquí y se imprimía una hoja en blanco
    win.listeners.afterprint()
    expect(inPage).toBe(false)  // se quita al terminar de imprimir
  })

  it('se quita una sola vez, aunque llegue también el respaldo de un minuto', () => {
    const win = fakeWindow()
    let removals = 0
    printThenRemove({ remove: () => { removals++ } }, { appendChild: () => {} }, win as never)
    win.listeners.afterprint()
    win.timers.forEach((t) => t())
    expect(removals).toBe(1)
  })
})
