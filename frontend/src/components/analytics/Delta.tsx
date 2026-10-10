import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { cn } from '@/lib/cn'

/**
 * Variación frente al período comparable. Sin base (el comparable fue 0 o no existe)
 * NO se inventa un porcentaje: se dice que no hay con qué comparar.
 * `inverse`: subir es malo (p. ej. mermas).
 */
export default function Delta({ pct, against, inverse = false }: { pct: number | null | undefined; against?: string; inverse?: boolean }) {
  if (pct === null || pct === undefined) {
    return <span className="text-xs text-ink-subtle">Sin base para comparar{against && ` con ${against}`}</span>
  }
  const flat = Math.abs(pct) < 0.05
  const good = flat ? null : (pct > 0) !== inverse
  const Icon = flat ? Minus : pct > 0 ? ArrowUpRight : ArrowDownRight
  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <span className={cn('inline-flex items-center gap-0.5 font-medium num',
        good === null ? 'text-ink-muted' : good ? 'text-success' : 'text-danger')}>
        <Icon size={13} aria-hidden />{flat ? '0%' : `${pct > 0 ? '+' : ''}${pct.toLocaleString('es-CO', { maximumFractionDigits: 1 })}%`}
      </span>
      {against && <span className="text-ink-muted truncate">vs {against}</span>}
    </span>
  )
}
