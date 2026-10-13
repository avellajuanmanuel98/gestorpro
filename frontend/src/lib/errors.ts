import { isAxiosError } from 'axios'

/** Convierte cualquier error de API en un mensaje legible para el usuario. */
export function getErrorMessage(err: unknown, fallback = 'Ocurrió un error. Intenta de nuevo.'): string {
  if (isAxiosError(err)) {
    if (!err.response) return 'No se puede conectar con el servidor. Revisa tu conexión.'
    const data = err.response.data as unknown
    if (typeof data === 'string' && data.trim() && data.length < 300 && !data.trimStart().startsWith('<')) return data
    if (data && typeof data === 'object') {
      const record = data as Record<string, unknown>
      if (typeof record.detail === 'string') return record.detail
      const messages = Object.values(record).flat().filter((m): m is string => typeof m === 'string')
      if (messages.length) return messages.join(' ')
    }
    // Sin un mensaje útil (p. ej. una página de error de un proxy): nada técnico ni en inglés
    return err.response.status >= 500 ? 'El servidor tuvo un problema. Intenta de nuevo en un momento.' : fallback
  }
  if (err instanceof Error && err.message) return err.message
  return fallback
}
