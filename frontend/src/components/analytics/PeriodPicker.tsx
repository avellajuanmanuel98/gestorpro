import type { PeriodInfo, PeriodPreset, PeriodQuery } from '@/api/analytics'
import { cn } from '@/lib/cn'
import { PRESETS } from '@/lib/period'

export default function PeriodPicker({ value, onChange, presets, info }: {
  value: PeriodQuery; onChange: (q: PeriodQuery) => void; presets?: PeriodPreset[]
  /** Si se pasa, se muestra contra qué se comparan las variaciones. */
  info?: PeriodInfo
}) {
  const shown = presets ? PRESETS.filter((p) => presets.includes(p.id)) : PRESETS
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div role="radiogroup" aria-label="Período" className="inline-flex flex-wrap gap-1 rounded-xl bg-surface-muted p-1">
        {shown.map((p) => (
          <button key={p.id} type="button" role="radio" aria-checked={value.period === p.id}
                  onClick={() => onChange(p.id === 'custom' ? { period: 'custom', from: value.from, to: value.to } : { period: p.id })}
                  className={cn('h-8 px-3 rounded-lg text-sm transition-colors',
                    value.period === p.id ? 'bg-surface text-ink font-medium shadow-sm' : 'text-ink-muted hover:text-ink')}>
            {p.label}
          </button>
        ))}
      </div>
      {value.period === 'custom' && (
        <div className="flex items-center gap-2 text-sm">
          <input type="date" aria-label="Desde" value={value.from ?? ''} max={value.to}
                 onChange={(e) => onChange({ ...value, from: e.target.value })}
                 className="h-9 rounded-lg border border-line-strong bg-surface px-2 text-ink" />
          <span className="text-ink-subtle">a</span>
          <input type="date" aria-label="Hasta" value={value.to ?? ''} min={value.from}
                 onChange={(e) => onChange({ ...value, to: e.target.value })}
                 className="h-9 rounded-lg border border-line-strong bg-surface px-2 text-ink" />
        </div>
      )}
      {info && (
        <p className="text-xs text-ink-muted">
          {info.label} · comparado con <span className="text-ink">{info.previous.label}</span>
          <span className="hidden sm:inline"> ({PRESETS.find((p) => p.id === info.preset)?.compare})</span>
        </p>
      )}
    </div>
  )
}
