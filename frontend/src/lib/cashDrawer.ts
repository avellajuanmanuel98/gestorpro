import { playCoins } from './coinSound'
import { useDisplayStore } from '@/store/displayStore'

/**
 * Abrir el cajón monedero sin vender (dar cambio, guardar un billete).
 *
 * El cajón no se conecta al computador: va con un cable RJ11 a la impresora de tickets, y se
 * abre cuando la impresora imprime con la opción "abrir cajón" activa en su driver de Windows.
 * Una página web no puede mandar la señal directa, así que se imprime un ticket mínimo que
 * deja constancia en papel de quién abrió el cajón y cuándo.
 */
export function openCashDrawer(userName: string) {
  if (useDisplayStore.getState().coinSound) playCoins()
  const ticket = document.createElement('div')
  ticket.className = 'print-ticket print-only font-mono text-[12px] leading-snug text-black bg-white'
  ticket.setAttribute('aria-hidden', 'true')
  const now = new Date().toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
  ticket.textContent = `Apertura de cajón · ${now} · ${userName}`
  printThenRemove(ticket, document.body, window)
}

/**
 * Imprime `el` y lo quita DESPUÉS de imprimir. Con Chrome en modo "imprimir sin preguntar"
 * (--kiosk-printing), window.print() vuelve enseguida y la página se imprime más tarde: si el
 * ticket se quitaba al volver, salía una hoja en blanco, la impresora no imprimía nada y el
 * cajón no se abría. Se quita en "afterprint" (o al minuto, por si ese evento no llega).
 */
export function printThenRemove(
  el: { remove: () => void },
  parent: { appendChild: (el: never) => unknown },
  win: Pick<Window, 'print' | 'addEventListener' | 'setTimeout'>,
) {
  parent.appendChild(el as never)
  let removed = false
  const cleanup = () => {
    if (!removed) { removed = true; el.remove() }
  }
  win.addEventListener('afterprint', cleanup, { once: true })
  win.setTimeout(cleanup, 60_000)
  win.print()
}
