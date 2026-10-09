import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { PaginatedResponse } from '@/types'

interface PaginationProps {
  data: Pick<PaginatedResponse<unknown>, 'count' | 'page' | 'page_size' | 'total_pages'> | undefined
  onPageChange: (page: number) => void
  /** Sustantivo en plural para el resumen: "clientes", "productos"… */
  noun: string
  isFetching?: boolean
}

const fmt = (n: number) => n.toLocaleString('es-CO')

/** Pie de tabla con paginación del servidor. Siempre muestra el total real. */
export default function Pagination({ data, onPageChange, noun, isFetching = false }: PaginationProps) {
  if (!data || data.count === 0) return null
  const from = (data.page - 1) * data.page_size + 1
  const to = Math.min(data.page * data.page_size, data.count)
  const btn = 'inline-flex items-center justify-center h-8 w-8 rounded-lg text-ink-muted hover:bg-surface-muted hover:text-ink disabled:opacity-40 disabled:pointer-events-none'

  return (
    <nav aria-label="Paginación" className="flex items-center justify-between gap-4 px-5 py-3 border-t border-line">
      <p className="text-xs text-ink-muted num" aria-live="polite">
        {fmt(from)}–{fmt(to)} de {fmt(data.count)} {noun}
        {isFetching && <span className="ml-2 text-ink-subtle">· actualizando…</span>}
      </p>
      {data.total_pages > 1 && (
        <div className="flex items-center gap-1">
          <button type="button" className={btn} disabled={data.page <= 1} onClick={() => onPageChange(data.page - 1)}
                  aria-label="Página anterior"><ChevronLeft size={16} /></button>
          <span className="text-xs text-ink-muted num px-2">Página {data.page} de {data.total_pages}</span>
          <button type="button" className={btn} disabled={data.page >= data.total_pages}
                  onClick={() => onPageChange(data.page + 1)} aria-label="Página siguiente"><ChevronRight size={16} /></button>
        </div>
      )}
    </nav>
  )
}
