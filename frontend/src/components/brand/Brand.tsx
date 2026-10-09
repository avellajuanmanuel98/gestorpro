import { cn } from '@/lib/cn'

/**
 * Marca: "Miga by GestorPro" para panaderías y "GestorPro" para el resto.
 * El símbolo es una forma simple (una "M" tinta con una miga de acento),
 * sin panes dibujados ni degradados.
 */
export function BrandMark({ isMiga = true, className }: { isMiga?: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn('w-7 h-7 shrink-0', className)} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--primary)" />
      <path d={isMiga ? 'M9 22V11.5l7 6.5 7-6.5V22' : 'M21.2 11.3A7 7 0 1 0 22.8 17.6H16.5'}
            fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="23.5" cy="8.5" r="3" fill="var(--accent)" />
    </svg>
  )
}

export default function Brand({ vertical, compact = false }: { vertical?: string; compact?: boolean }) {
  const isMiga = vertical === 'bakery'
  return (
    <div className="flex items-center gap-2.5 min-w-0">
      <BrandMark isMiga={isMiga} />
      {!compact && (
        <div className="leading-none min-w-0">
          <p className="text-[15px] font-semibold tracking-tight text-ink">{isMiga ? 'Miga' : 'GestorPro'}</p>
          {isMiga && <p className="mt-0.5 text-[10px] font-medium tracking-wide text-ink-subtle">by GestorPro</p>}
        </div>
      )}
    </div>
  )
}
