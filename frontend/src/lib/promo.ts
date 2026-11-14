/**
 * Línea de publicidad del sistema al pie del ticket: cada cliente de la tienda que recibe
 * un ticket ve cómo conseguir GestorPro. Discreta, debajo de todo, para no competir con el
 * nombre del negocio ni con el total.
 */
export const PROMO_WHATSAPP = '302 205 2551'

export function receiptPromo(vertical?: string) {
  return {
    system: vertical === 'bakery' ? 'Sistema Miga by GestorPro' : 'Sistema GestorPro',
    question: '¿Quieres uno para tu negocio?',
    contact: `WhatsApp ${PROMO_WHATSAPP}`,
  }
}
