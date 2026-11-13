/**
 * Abrir el cajón monedero sin vender (dar cambio, guardar un billete).
 *
 * El cajón no se conecta al computador: va con un cable RJ11 a la impresora de tickets, y se
 * abre cuando la impresora imprime con la opción "abrir cajón" activa en su driver de Windows.
 * Una página web no puede mandar la señal directa, así que se imprime un ticket mínimo que
 * deja constancia en papel de quién abrió el cajón y cuándo.
 */
export function openCashDrawer(userName: string) {
  const ticket = document.createElement('div')
  ticket.className = 'print-ticket print-only font-mono text-[12px] leading-snug text-black bg-white'
  ticket.setAttribute('aria-hidden', 'true')
  const now = new Date().toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
  ticket.textContent = `Apertura de cajón · ${now} · ${userName}`
  document.body.appendChild(ticket)
  try {
    window.print()
  } finally {
    ticket.remove()
  }
}
