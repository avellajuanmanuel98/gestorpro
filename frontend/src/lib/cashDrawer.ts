import { playCoins } from './coinSound'
import { useDisplayStore } from '@/store/displayStore'

/**
 * El cajón no se conecta al computador: va con un cable RJ11 a la impresora de tickets, y se
 * abre cuando la impresora imprime con la opción "abrir cajón" activa en su driver de Windows.
 * Una página web no puede mandar la señal directa, así que para abrirlo se imprime una línea
 * mínima (que además deja constancia en papel de cuándo y por qué se abrió).
 */

/** Botón "Abrir cajón": abrirlo sin vender (dar cambio, guardar un billete). */
export function openCashDrawer(userName: string) {
  if (useDisplayStore.getState().coinSound) playCoins()
  const now = new Date().toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
  printDrawerSlip(`Apertura de cajón · ${now} · ${userName}`)
}

/**
 * Imprime SOLO una línea, aunque en la página haya un ticket listo para imprimir (el de la
 * venta recién cobrada): mientras se imprime, el cuerpo lleva la clase "printing-drawer" y
 * los estilos de impresión ocultan cualquier otro ticket.
 */
export function printDrawerSlip(text: string) {
  const slip = document.createElement('div')
  slip.className = 'print-ticket drawer-slip print-only font-mono text-[11px] leading-snug text-black bg-white'
  slip.setAttribute('aria-hidden', 'true')
  slip.textContent = text
  document.body.classList.add('printing-drawer')
  printThenRemove(slip, document.body, window, () => document.body.classList.remove('printing-drawer'))
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
  onDone?: () => void,
) {
  parent.appendChild(el as never)
  let removed = false
  const cleanup = () => {
    if (removed) return
    removed = true
    el.remove()
    onDone?.()
  }
  win.addEventListener('afterprint', cleanup, { once: true })
  win.setTimeout(cleanup, 60_000)
  win.print()
}
