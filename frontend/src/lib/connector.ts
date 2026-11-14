/**
 * Conector de Miga: programa pequeño en el computador de la caja (carpeta conector/ del
 * repositorio) que abre el cajón con el comando directo de la impresora, SIN imprimir.
 * Chrome no deja que una página mande ese comando; el conector sí, y solo escucha en el
 * propio equipo (127.0.0.1). Si no está instalado o no responde, Miga sigue abriendo el
 * cajón imprimiendo una línea mínima.
 */
const BASE = 'http://127.0.0.1:17777'

async function call(path: string, method: 'GET' | 'POST', timeoutMs: number): Promise<boolean> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(`${BASE}${path}`, {
      method, signal: ctrl.signal, cache: 'no-store',
      // Chrome (acceso a la red local): avisa que el destino es este mismo equipo
      targetAddressSpace: 'loopback',
    } as RequestInit)
    if (!res.ok) return false
    const body = await res.json().catch(() => null) as { ok?: boolean } | null
    return body?.ok === true
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

/** Pide al conector abrir el cajón. true = abierto sin imprimir; false = usar el respaldo. */
export const openDrawerViaConnector = () => call('/cajon', 'POST', 1500)

/** ¿Está corriendo el conector en este computador? */
export const connectorAvailable = () => call('/estado', 'GET', 1000)
