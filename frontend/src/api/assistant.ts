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

import { API_BASE_URL, refreshAccessToken, tokenStorage } from './client'

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
  const send = (token: string | null) => fetch(`${API_BASE_URL}/assistant/chat/`, {
    method:  'POST',
    headers: {
      'Content-Type':  'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body:   JSON.stringify({ message }),
    signal,
  })

  let response = await send(tokenStorage.access)
  if (response.status === 401) {
    try {
      response = await send(await refreshAccessToken())
    } catch {
      callbacks.onError('Tu sesión expiró. Vuelve a iniciar sesión.')
      return
    }
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    callbacks.onError(err?.error ?? err?.detail ?? `Error del servidor (${response.status})`)
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
