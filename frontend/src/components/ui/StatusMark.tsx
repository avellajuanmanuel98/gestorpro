import { useId } from 'react'
import { cn } from '@/lib/cn'

/**
 * Lenguaje propio de estados (reemplaza las "píldoras" de color).
 *
 * - La FORMA comunica el estado y el color lo refuerza: se entiende sin
 *   distinguir colores y también impreso en blanco y negro.
 * - El símbolo es una "miga" orgánica, la misma idea de la marca.
 * - El texto va en tinta normal. Solo el símbolo lleva color, así una tabla
 *   llena de estados no se convierte en un mosaico.
 */

export type StatusTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'accent'
export type StatusGlyph = 'solid' | 'hollow' | 'half' | 'paused'

const toneClass: Record<StatusTone, string> = {
  neutral: 'text-ink-subtle',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
  info: 'text-info',
  accent: 'text-accent',
}

// Contorno irregular de una miga (viewBox 16×16)
const CRUMB = 'M6.6 1.8l3.6.4 3 2.3 1.1 3.3-1.2 3.6-3.1 2.5-3.8.3-3-1.7-1.5-3.2.5-3.8 2.4-2.6z'

export function StatusGlyphIcon({ glyph, tone, className }: { glyph: StatusGlyph; tone: StatusTone; className?: string }) {
  const id = useId()
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={cn('w-[15px] h-[15px] shrink-0', toneClass[tone], className)}>
      {glyph === 'solid' && <path d={CRUMB} fill="currentColor" stroke="currentColor" strokeWidth="1" strokeLinejoin="round" />}
      {glyph === 'hollow' && (
        <path d={CRUMB} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" strokeDasharray="2.2 2" strokeLinecap="round" />
      )}
      {glyph === 'half' && (
        <>
          <clipPath id={id}><rect x="0" y="0" width="8" height="16" /></clipPath>
          <path d={CRUMB} fill="currentColor" clipPath={`url(#${id})`} />
          <path d={CRUMB} fill="none" stroke="currentColor" strokeWidth="1.5" />
        </>
      )}
      {glyph === 'paused' && (
        <>
          <path d={CRUMB} fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M6.6 5.9v4.4M9.6 5.9v4.4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </>
      )}
    </svg>
  )
}

export interface StatusSpec {
  label: string
  tone: StatusTone
  glyph: StatusGlyph
}

/** Estado de algo que está vivo o no: clientes, productos, usuarios, empleados… */
export default function StatusMark({ status, className }: { status: StatusSpec; className?: string }) {
  const quiet = status.glyph === 'hollow'
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap',
                        quiet ? 'text-ink-muted' : 'text-ink', className)}>
      <StatusGlyphIcon glyph={status.glyph} tone={status.tone} />
      {status.label}
    </span>
  )
}

// ── Documentos: el estado como posición en su ciclo de vida ────────────────

export interface LifecycleSpec {
  label: string
  tone: StatusTone
  /** Tramos recorridos del ciclo (borrador → enviada → pagada). */
  step: 1 | 2 | 3
  /** Vencida: el tramo siguiente queda "en deuda" (punteado). */
  stalled?: boolean
  /** Anulada: el ciclo se corta. */
  voided?: boolean
}

const barTone: Record<StatusTone, string> = {
  neutral: 'bg-ink-subtle',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
  info: 'bg-info',
  accent: 'bg-accent',
}

/**
 * Riel de tres tramos que muestra en qué punto del ciclo va el documento:
 * se lee de un vistazo cuánto le falta para cerrarse.
 */
export function LifecycleMark({ status, className }: { status: LifecycleSpec; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2 text-[13px] whitespace-nowrap',
                        status.voided ? 'text-ink-muted' : 'text-ink', className)}>
      <span className="relative inline-flex items-center gap-[3px]" aria-hidden="true">
        {[1, 2, 3].map((n) => {
          const done = !status.voided && n <= status.step
          const owed = status.stalled && n === status.step + 1
          return (
            <span key={n} className={cn(
              'h-[5px] w-[9px] rounded-full',
              done ? barTone[status.tone]
                : owed ? 'border border-dashed border-danger bg-transparent'
                : 'bg-line-strong/60',
            )} />
          )
        })}
        {status.voided && <span className="absolute inset-x-[-2px] top-1/2 h-px -rotate-12 bg-ink-muted" />}
      </span>
      <span className={cn(status.voided && 'line-through decoration-ink-subtle')}>{status.label}</span>
    </span>
  )
}

const stampTone: Record<StatusTone, string> = {
  neutral: 'text-ink-muted border-ink-subtle',
  success: 'text-success border-success',
  warning: 'text-warning border-warning',
  danger: 'text-danger border-danger',
  info: 'text-info border-info',
  accent: 'text-accent-ink border-accent',
}

/** Sello de documento, como el "PAGADO" que se estampa sobre una factura de papel. */
export function StatusStamp({ status, className }: { status: LifecycleSpec; className?: string }) {
  return (
    <span className={cn(
      'inline-block -rotate-3 select-none rounded-[6px] border-2 px-2.5 py-1',
      'text-[11px] font-bold uppercase tracking-[0.18em]',
      status.step === 1 && !status.voided ? 'border-dashed' : 'border-double border-[3px]',
      stampTone[status.tone], className,
    )}>
      {status.label}
    </span>
  )
}
