import { cn } from '@/lib/cn'
import { Skeleton } from './Skeleton'

interface KpiTileProps {
  label: string
  value: React.ReactNode
  /** Contexto real (p. ej. "3 documentos"). Nunca una variación inventada. */
  hint?: React.ReactNode
  tone?: 'default' | 'warning' | 'danger'
  loading?: boolean
  /** Si el rol o el plan no permiten la métrica, se explica en lugar de mostrar 0 */
  unavailable?: string
}

export default function KpiTile({ label, value, hint, tone = 'default', loading, unavailable }: KpiTileProps) {
  return (
    <div className="bg-surface border border-line rounded-xl px-5 py-4 min-w-0">
      <p className="text-xs font-medium text-ink-muted">{label}</p>
      {loading ? (
        <div className="mt-2 space-y-2"><Skeleton height={26} width="60%" /><Skeleton height={11} width="40%" /></div>
      ) : unavailable ? (
        <p className="mt-2 text-sm text-ink-subtle">{unavailable}</p>
      ) : (
        <>
          <p className={cn('mt-1.5 text-2xl font-semibold tracking-tight num truncate',
            tone === 'danger' ? 'text-danger' : tone === 'warning' ? 'text-warning' : 'text-ink')}>
            {value}
          </p>
          {hint && <p className="mt-1 text-xs text-ink-muted">{hint}</p>}
        </>
      )}
    </div>
  )
}
