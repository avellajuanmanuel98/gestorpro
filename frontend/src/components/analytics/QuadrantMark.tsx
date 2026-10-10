import type { Quadrant } from '@/api/analytics'
import { cn } from '@/lib/cn'

/** Posición en la matriz volumen × margen (arriba = más margen, derecha = más volumen). */
const CELL: Record<Quadrant, number> = { puzzle: 0, star: 1, dog: 2, workhorse: 3 }
const TONE: Record<Quadrant, string> = {
  star: 'bg-success', workhorse: 'bg-info', puzzle: 'bg-warning', dog: 'bg-ink-subtle',
}

export default function QuadrantMark({ quadrant, label, advice, showLabel = true }: {
  quadrant: Quadrant; label?: string; advice?: string; showLabel?: boolean
}) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink-muted" title={advice}>
      <span aria-hidden className="grid grid-cols-2 gap-[2px] w-3.5 h-3.5 shrink-0">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className={cn('rounded-[1.5px]', i === CELL[quadrant] ? TONE[quadrant] : 'bg-line-strong/60')} />
        ))}
      </span>
      {showLabel ? <span>{label}</span> : <span className="sr-only">{label}</span>}
    </span>
  )
}
