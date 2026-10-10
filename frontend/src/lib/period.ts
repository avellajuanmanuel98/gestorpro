import { useSearchParams } from 'react-router-dom'
import type { PeriodPreset, PeriodQuery } from '@/api/analytics'

export const PRESETS: { id: PeriodPreset; label: string; compare: string }[] = [
  { id: 'today', label: 'Hoy', compare: 'mismo día de la semana pasada' },
  { id: 'yesterday', label: 'Ayer', compare: 'mismo día de la semana anterior' },
  { id: '7d', label: '7 días', compare: '7 días anteriores' },
  { id: '30d', label: '30 días', compare: '30 días anteriores' },
  { id: 'this_month', label: 'Este mes', compare: 'mismos días del mes pasado' },
  { id: 'last_month', label: 'Mes pasado', compare: 'mes anterior' },
  { id: 'this_year', label: 'Este año', compare: 'mismo tramo del año pasado' },
  { id: 'custom', label: 'Rango', compare: 'período anterior de igual duración' },
]

/** Período en la URL (?period=&from=&to=): se puede compartir y sobrevive a recargar. */
export function usePeriod(fallback: PeriodPreset = 'today'): [PeriodQuery, (q: PeriodQuery) => void] {
  const [params, setParams] = useSearchParams()
  const raw = params.get('period') as PeriodPreset | null
  const preset = raw && PRESETS.some((p) => p.id === raw) ? raw : fallback
  const query: PeriodQuery = preset === 'custom'
    ? { period: preset, from: params.get('from') ?? undefined, to: params.get('to') ?? undefined }
    : { period: preset }
  const set = (q: PeriodQuery) => setParams((prev) => {
    const next = new URLSearchParams(prev)
    next.set('period', q.period)
    for (const k of ['from', 'to'] as const) {
      const v = q[k]
      if (q.period === 'custom' && v) next.set(k, v)
      else next.delete(k)
    }
    return next
  }, { replace: true })
  return [query, set]
}

/** Un rango personalizado solo se consulta cuando tiene ambas fechas. */
export const isReady = (q: PeriodQuery) => q.period !== 'custom' || (!!q.from && !!q.to)
