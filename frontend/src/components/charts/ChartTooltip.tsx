import { formatCOP } from '@/lib/money'

interface ChartTooltipProps {
  active?: boolean
  label?: string
  payload?: { value: number; name?: string }[]
  money?: boolean
  unit?: string
}

/** Tooltip estándar de gráficos (tokens de superficie, cifras tabulares). */
export default function ChartTooltip({ active, payload, label, money = false, unit = '' }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  const value = payload[0].value
  return (
    <div className="bg-surface border border-line rounded-lg shadow-overlay px-3 py-2 text-sm">
      {label && <p className="text-xs text-ink-muted">{label}</p>}
      <p className="font-semibold text-ink num">{money ? formatCOP(value) : `${value.toLocaleString('es-CO')}${unit}`}</p>
    </div>
  )
}
