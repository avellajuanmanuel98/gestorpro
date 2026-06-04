/**
 * Cliente para el endpoint de streaming del asistente IA.
 *
 * Usa la Fetch API con ReadableStream en lugar de EventSource
 * para poder enviar un body POST con el mensaje del usuario.
 *
 * Cada chunk SSE tiene el formato:
 *   data: {"type": "delta", "text": "..."}
 *   data: {"type": "done"}
 *   data: {"type": "error", "message": "..."}
 */

// En desarrollo usa localhost:8000, en producción usa VITE_API_URL (Railway)
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const API_BASE = `${BASE_URL}/api`

interface StreamCallbacks {
  onDelta:  (text: string) => void
  onDone:   () => void
  onError:  (message: string) => void
}

export async function streamAssistantMessage(
  message: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const token = localStorage.getItem('access_token')

  const response = await fetch(`${API_BASE}/assistant/chat/`, {
    method:  'POST',
    headers: {
      'Content-Type':  'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body:   JSON.stringify({ message }),
    signal,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    callbacks.onError(err?.error ?? `Error del servidor (${response.status})`)
    return
  }

  const reader  = response.body!.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE puede llegar en chunks parciales — procesamos línea por línea
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''           // la última línea puede estar incompleta

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue

      const jsonStr = trimmed.slice(5).trim()
      if (!jsonStr) continue

      try {
        const event = JSON.parse(jsonStr)

        if (event.type === 'delta') {
          callbacks.onDelta(event.text ?? '')
        } else if (event.type === 'done') {
          callbacks.onDone()
          return
        } else if (event.type === 'error') {
          callbacks.onError(event.message ?? 'Error desconocido')
          return
        }
      } catch {
        // Ignorar chunks mal formados
      }
    }
  }

  callbacks.onDone()
}
