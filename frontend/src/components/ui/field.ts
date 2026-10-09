/** Estilo compartido de los controles de formulario (input, select, textarea). */
export const controlClass = [
  'w-full rounded-lg border bg-surface text-sm text-ink placeholder:text-ink-subtle',
  'transition-colors focus:outline-none focus:border-focus focus:ring-2 focus:ring-focus/20',
  'disabled:opacity-60 disabled:cursor-not-allowed',
].join(' ')

/** Solo para campos de texto: un <select> cuenta como :read-only en CSS y se vería deshabilitado. */
export const readOnlyClass = 'read-only:bg-surface-muted read-only:text-ink-muted'

export const labelClass = 'block text-sm font-medium text-ink'
export const hintClass = 'text-xs text-ink-muted'
export const errorClass = 'text-xs text-danger'
