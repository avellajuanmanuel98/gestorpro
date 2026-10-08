import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { PaginatedResponse } from '@/types'

interface PaginationProps {
  data:         Pick<PaginatedResponse<unknown>, 'count' | 'page' | 'page_size' | 'total_pages'> | undefined
  onPageChange: (page: number) => void
  /** Sustantivo en plural para el resumen: "clientes", "productos"… */
  noun:         string
  isFetching?:  boolean
}

/**
 * Pie de tabla con paginación real del servidor. Siempre muestra el total,
 * para que el usuario nunca crea que solo existen los registros visibles.
 */
export default function Pagination({ data, onPageChange, noun, isFetching = false }: PaginationProps) {
  if (!data || data.count === 0) return null

  const from = (data.page - 1) * data.page_size + 1
  const to = Math.min(data.page * data.page_size, data.count)
  const canPrev = data.page > 1
  const canNext = data.page < data.total_pages

  const buttonClass = [
    'inline-flex items-center justify-center h-8 w-8 rounded-lg transition-colors',
    'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900',
    'dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100',
    'disabled:opacity-40 disabled:pointer-events-none',
  ].join(' ')

  return (
    <nav
      aria-label="Paginación"
      className="flex items-center justify-between gap-4 px-6 py-3 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50/60 dark:bg-zinc-800/20"
    >
      <p className="text-xs text-zinc-500 dark:text-zinc-400 tabular-nums" aria-live="polite">
        {from.toLocaleString('es-CO')}–{to.toLocaleString('es-CO')} de {data.count.toLocaleString('es-CO')} {noun}
        {isFetching && <span className="ml-2 text-zinc-400">· actualizando…</span>}
      </p>
      {data.total_pages > 1 && (
        <div className="flex items-center gap-1">
          <button type="button" className={buttonClass} disabled={!canPrev}
                  onClick={() => onPageChange(data.page - 1)} aria-label="Página anterior">
            <ChevronLeft size={16} />
          </button>
          <span className="text-xs text-zinc-600 dark:text-zinc-300 tabular-nums px-2">
            Página {data.page} de {data.total_pages}
          </span>
          <button type="button" className={buttonClass} disabled={!canNext}
                  onClick={() => onPageChange(data.page + 1)} aria-label="Página siguiente">
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </nav>
  )
}
