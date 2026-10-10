const dateTime = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short' })
const date = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium' })

export function formatDateTime(value: string | null | undefined): string {
  return value ? dateTime.format(new Date(value)) : '—'
}

export function formatDate(value: string | null | undefined): string {
  return value ? date.format(new Date(value)) : '—'
}

const time = new Intl.DateTimeFormat('es-CO', { timeStyle: 'short' })

export function formatTime(value: string | null | undefined): string {
  return value ? time.format(new Date(value)) : '—'
}

/** Fecha local de hoy como AAAA-MM-DD (para filtros). */
export function todayISO(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
