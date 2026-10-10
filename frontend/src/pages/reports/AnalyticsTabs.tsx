import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart2, Download, Wallet } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { analyticsApi, type BreakdownBy, type CashSessionRow, type PeriodQuery, type ProductRow, type Quadrant } from '@/api/analytics'
import ChartTooltip from '@/components/charts/ChartTooltip'
import Delta from '@/components/analytics/Delta'
import QuadrantMark from '@/components/analytics/QuadrantMark'
import Button from '@/components/ui/Button'
import { Card, CardHeader } from '@/components/ui/Card'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import KpiTile from '@/components/ui/KpiTile'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatQty } from '@/lib/catalog'
import { axisTick } from '@/lib/charts'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP, formatCompactNumber, toDisplayNumber } from '@/lib/money'
import { toast } from '@/store/toastStore'

const NoData = ({ text, description }: { text: string; description?: string }) =>
  <EmptyState compact icon={<BarChart2 size={20} />} title={text} description={description} />
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('es-CO')}%`)

/** Exporta en el servidor con los mismos filtros (CSV con ; y coma decimal: abre bien en Excel en español). */
function ExportButton({ run }: { run: () => Promise<void> }) {
  const [busy, setBusy] = useState(false)
  return (
    <Button variant="outline" size="sm" icon={<Download size={14} />} loading={busy}
            onClick={async () => {
              setBusy(true)
              try { await run() } catch (e) { toast.error(getErrorMessage(e)) } finally { setBusy(false) }
            }}>
      Exportar CSV
    </Button>
  )
}

// ── Ventas ────────────────────────────────────────────────────────────────────

const BREAKDOWNS: { id: BreakdownBy; label: string }[] = [
  { id: 'day', label: 'Día' }, { id: 'weekday', label: 'Día de la semana' }, { id: 'method', label: 'Medio de pago' },
  { id: 'cashier', label: 'Cajero' }, { id: 'category', label: 'Categoría' },
]

export function SalesTab({ period }: { period: PeriodQuery }) {
  const [by, setBy] = useState<BreakdownBy>('day')
  const summary = useQuery({ queryKey: ['analytics', 'summary', period], queryFn: () => analyticsApi.summary(period) })
  const data = useQuery({ queryKey: ['analytics', 'breakdown', period, by], queryFn: () => analyticsApi.breakdown(period, by) })
  const k = summary.data?.kpis
  const rows = (data.data?.rows ?? []).map((r) => ({ ...r, value: toDisplayNumber(r.sales) }))
  const total = rows.reduce((s, r) => s + r.value, 0)
  const vertical = by !== 'day' && by !== 'weekday'
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiTile label="Ventas (con IVA)" loading={summary.isLoading} value={formatCOP(k?.sales.value, { compact: true })}
                 hint={k && <Delta pct={k.sales.change_pct} />} />
        <KpiTile label="Transacciones" loading={summary.isLoading} value={k?.transactions.value ?? 0}
                 hint={k && <Delta pct={k.transactions.change_pct} />} />
        <KpiTile label="Ticket promedio" loading={summary.isLoading} value={k?.average_ticket.value ? formatCOP(k.average_ticket.value) : '—'}
                 hint={k && <Delta pct={k.average_ticket.change_pct} />} />
        <KpiTile label="Período comparable" loading={summary.isLoading} value={formatCOP(k?.sales.previous, { compact: true })}
                 hint={summary.data?.period.previous.label} />
      </div>
      <Card>
        <CardHeader title="Ventas por…"
                    description={<span className="inline-flex flex-wrap gap-1 mt-1">
                      {BREAKDOWNS.map((b) => (
                        <button key={b.id} type="button" aria-pressed={by === b.id} onClick={() => setBy(b.id)}
                                className={cn('h-7 px-2.5 rounded-full text-xs border transition-colors',
                                  by === b.id ? 'bg-ink text-canvas border-ink' : 'border-line-strong text-ink-muted hover:text-ink')}>
                          {b.label}
                        </button>
                      ))}
                    </span>}
                    actions={<ExportButton run={() => analyticsApi.exportCsv('breakdown', period, { by })} />} />
        <div className="grid gap-4 lg:grid-cols-[3fr_2fr] px-2 pb-4">
          {data.isLoading ? <div className="px-3"><Skeleton height={240} /></div> : !rows.length ? (
            <NoData text="Sin ventas en el período" />
          ) : (
            <ResponsiveContainer width="100%" height={vertical ? Math.max(180, rows.length * 38) : 260}>
              {vertical ? (
                <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
                  <CartesianGrid horizontal={false} stroke="var(--chart-grid)" />
                  <XAxis type="number" tickLine={false} axisLine={false} tick={{ ...axisTick, fontSize: 11 }} tickFormatter={formatCompactNumber} />
                  <YAxis type="category" dataKey="label" width={130} tickLine={false} axisLine={false} tick={axisTick} />
                  <Tooltip content={<ChartTooltip money />} cursor={{ fill: 'var(--surface-muted)' }} />
                  <Bar dataKey="value" fill="var(--chart-1)" radius={[0, 4, 4, 0]} maxBarSize={22} />
                </BarChart>
              ) : (
                <BarChart data={rows} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={axisTick} />
                  <YAxis tickLine={false} axisLine={false} width={56} tick={{ ...axisTick, fontSize: 11 }} tickFormatter={formatCompactNumber} />
                  <Tooltip content={<ChartTooltip money />} cursor={{ fill: 'var(--surface-muted)' }} />
                  <Bar dataKey="value" fill="var(--chart-1)" radius={[4, 4, 0, 0]} maxBarSize={36} />
                </BarChart>
              )}
            </ResponsiveContainer>
          )}
          {!!rows.length && (
            <table className="w-full text-sm self-start">
              <thead className="text-xs text-ink-muted"><tr className="border-b border-line">
                <th className="text-left font-medium py-2 px-3">{BREAKDOWNS.find((b) => b.id === by)?.label}</th>
                <th className="text-right font-medium py-2 px-3">Ventas</th><th className="text-right font-medium py-2 px-3">%</th>
                <th className="text-right font-medium py-2 px-3">Trans.</th></tr></thead>
              <tbody className="divide-y divide-line">
                {rows.map((r) => (
                  <tr key={String(r.key)}>
                    <td className="py-1.5 px-3 text-ink">{r.label}</td>
                    <td className="py-1.5 px-3 text-right num text-ink">{formatCOP(r.sales)}</td>
                    <td className="py-1.5 px-3 text-right num text-ink-muted">{total ? Math.round((r.value / total) * 100) : 0}%</td>
                    <td className="py-1.5 px-3 text-right num text-ink-muted">{r.transactions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        {by === 'method' && !!rows.length && (
          <p className="px-5 pb-4 text-xs text-ink-muted">Por medio de pago se suma lo aplicado a cada venta (una venta con pago mixto cuenta en ambos medios).</p>
        )}
      </Card>
    </div>
  )
}

// ── Rentabilidad ──────────────────────────────────────────────────────────────

export function ProfitTab({ period }: { period: PeriodQuery }) {
  const { data, isLoading } = useQuery({ queryKey: ['analytics', 'products', period], queryFn: () => analyticsApi.products(period) })
  const summary = useQuery({ queryKey: ['analytics', 'summary', period], queryFn: () => analyticsApi.summary(period) })
  const [filter, setFilter] = useState<Quadrant | null>(null)
  const costs = !!data?.costs
  const rows = (data?.rows ?? []).filter((r) => Number(r.units) > 0)
  const classified = rows.filter((r) => r.quadrant)
  const shown = filter ? rows.filter((r) => r.quadrant === filter) : rows
  const k = summary.data?.kpis
  const columns: Column<ProductRow>[] = [
    { key: 'name', header: 'Producto', primary: true, cell: (r) => (
      <div className="min-w-0"><p className="font-medium text-ink truncate">{r.name}</p>
        <p className="text-xs text-ink-muted">{r.category ?? 'Sin categoría'}</p></div>
    ) },
    { key: 'units', header: 'Vendido', align: 'right', cell: (r) => formatQty(r.units, r.unit) },
    { key: 'revenue', header: 'Ingreso sin IVA', align: 'right', cell: (r) => formatCOP(r.revenue) },
    ...(costs ? [
      { key: 'cost', header: 'Costo', align: 'right' as const, hideOnMobile: true, cell: (r: ProductRow) => formatCOP(r.cost) },
      { key: 'profit', header: 'Utilidad', align: 'right' as const, cell: (r: ProductRow) =>
        <span className={cn('font-medium', Number(r.gross_profit) < 0 ? 'text-danger' : 'text-ink')}>{formatCOP(r.gross_profit)}</span> },
      { key: 'margin', header: 'Margen', align: 'right' as const, cell: (r: ProductRow) => pct(r.margin_pct) },
      { key: 'quadrant', header: 'Clasificación', hideOnMobile: true, cell: (r: ProductRow) => r.quadrant
        ? <QuadrantMark quadrant={r.quadrant} label={r.quadrant_label} advice={r.quadrant_advice} />
        : <span className="text-xs text-ink-subtle">—</span> },
    ] : []),
  ]
  return (
    <div className="space-y-4">
      {costs && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <KpiTile label="Utilidad bruta" loading={summary.isLoading} value={formatCOP(k?.gross_profit?.value, { compact: true })}
                   hint={k && <Delta pct={k.gross_profit?.change_pct} />} />
          <KpiTile label="Costo de ventas" loading={summary.isLoading} value={formatCOP(k?.cost_of_sales?.value, { compact: true })}
                   hint="Costo promedio congelado al vender" />
          <KpiTile label="Margen bruto" loading={summary.isLoading} value={pct(k?.gross_margin_pct)} hint="Sobre ventas sin IVA" />
          <KpiTile label="Mermas (a costo)" loading={summary.isLoading} value={formatCOP(k?.waste_cost?.value, { compact: true })}
                   hint={k && <Delta pct={k.waste_cost?.change_pct} inverse />} />
        </div>
      )}
      {costs && (
        <Card>
          <CardHeader title="Matriz volumen × margen"
                      description={classified.length
                        ? 'Cada producto frente a la mediana de unidades vendidas y de utilidad por unidad. Toca un cuadrante para filtrar la tabla.'
                        : 'Se necesitan al menos 4 productos vendidos con costo registrado para clasificarlos.'} />
          {!!classified.length && (
            <div className="grid grid-cols-2 gap-2 px-5 pb-5">
              {(['puzzle', 'star', 'dog', 'workhorse'] as Quadrant[]).map((q) => {
                const items = classified.filter((r) => r.quadrant === q)
                const sample = items[0]
                return (
                  <button key={q} type="button" aria-pressed={filter === q} onClick={() => setFilter(filter === q ? null : q)}
                          className={cn('text-left rounded-xl border p-3 transition-colors min-h-28',
                            filter === q ? 'border-ink bg-surface-muted' : 'border-line hover:bg-surface-muted/60')}>
                    <div className="flex items-center justify-between">
                      <QuadrantMark quadrant={q} label={sample?.quadrant_label ?? LABELS[q]} />
                      <span className="text-xs text-ink-subtle num">{items.length}</span>
                    </div>
                    <p className="mt-1 text-xs text-ink-muted">{ADVICE[q]}</p>
                    <p className="mt-2 text-sm text-ink line-clamp-2">{items.map((r) => r.name).join(', ') || '—'}</p>
                  </button>
                )
              })}
              <p className="col-span-2 flex justify-between text-[11px] text-ink-subtle"><span>Arriba: más utilidad por unidad · ← menos vendido</span><span>más vendido →</span></p>
            </div>
          )}
        </Card>
      )}
      <Card>
        <CardHeader title={filter ? `Productos: ${LABELS[filter]}` : 'Rentabilidad por producto'}
                    description={costs ? 'Utilidad = ingreso sin IVA − costo congelado en cada venta' : 'Tu rol no incluye costos: se muestran unidades e ingresos.'}
                    actions={<div className="flex gap-2">
                      {filter && <Button variant="ghost" size="sm" onClick={() => setFilter(null)}>Ver todos</Button>}
                      <ExportButton run={() => analyticsApi.exportCsv('products', period)} />
                    </div>} />
        <DataTable caption="Rentabilidad por producto" columns={columns} rows={shown} rowKey={(r) => r.item} isLoading={isLoading}
                   empty={<NoData text="Sin ventas en el período" />} />
      </Card>
    </div>
  )
}

const LABELS: Record<Quadrant, string> = { star: 'Estrella', workhorse: 'Caballo de batalla', puzzle: 'Enigma', dog: 'Perro' }
const ADVICE: Record<Quadrant, string> = {
  star: 'Se vende mucho y deja buen margen.', workhorse: 'Se vende mucho, deja poco: revisa costo o precio.',
  puzzle: 'Deja buen margen, se vende poco: promociónalo.', dog: 'Se vende poco y deja poco: reformula o retira.',
}

// ── Producción y mermas ───────────────────────────────────────────────────────

export function ProductionWasteTab({ period, canWaste }: { period: PeriodQuery; canWaste: boolean }) {
  const products = useQuery({ queryKey: ['analytics', 'products', period], queryFn: () => analyticsApi.products(period) })
  const waste = useQuery({ queryKey: ['analytics', 'waste', period], queryFn: () => analyticsApi.waste(period), enabled: canWaste })
  const rows = (products.data?.rows ?? []).filter((r) => Number(r.produced) > 0 || Number(r.wasted) > 0)
    .sort((a, b) => (b.waste_rate_pct ?? -1) - (a.waste_rate_pct ?? -1))
  const costs = waste.data?.total_cost != null
  const reasons = (waste.data?.by_reason ?? []).map((r) => ({ ...r, value: costs ? toDisplayNumber(r.cost) : r.records }))
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Producido, vendido y perdido" description="Tasa de merma = unidades perdidas ÷ unidades producidas en el período" />
        {products.isLoading ? <div className="px-5 pb-5"><Skeleton height={160} /></div> : !rows.length ? (
          <NoData text="Sin producción ni mermas en el período" description="Registra la producción y las mermas para ver aquí cuánto se pierde de cada producto." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-ink-muted bg-surface-muted/60"><tr>
                <th className="text-left font-medium py-2 px-5">Producto</th><th className="text-right font-medium py-2 px-3">Producido</th>
                <th className="text-right font-medium py-2 px-3">Vendido</th><th className="text-right font-medium py-2 px-3">Merma</th>
                <th className="text-left font-medium py-2 px-5 w-48">Tasa de merma</th></tr></thead>
              <tbody className="divide-y divide-line">
                {rows.map((r) => (
                  <tr key={r.item}>
                    <td className="py-2 px-5 text-ink">{r.name}</td>
                    <td className="py-2 px-3 text-right num">{formatQty(r.produced, r.unit)}</td>
                    <td className="py-2 px-3 text-right num">{formatQty(r.units, r.unit)}</td>
                    <td className="py-2 px-3 text-right num text-warning">{Number(r.wasted) ? formatQty(r.wasted, r.unit) : '—'}</td>
                    <td className="py-2 px-5">
                      {r.waste_rate_pct == null ? <span className="text-xs text-ink-subtle">Sin producción registrada</span> : (
                        <span className="flex items-center gap-2">
                          <span className="flex-1 h-1.5 rounded-full bg-surface-muted overflow-hidden" aria-hidden>
                            <span className={cn('block h-full rounded-full', r.waste_rate_pct >= 10 ? 'bg-danger' : r.waste_rate_pct >= 5 ? 'bg-warning' : 'bg-success')}
                                  style={{ width: `${Math.min(100, r.waste_rate_pct)}%` }} />
                          </span>
                          <span className="w-12 text-right num text-ink">{pct(r.waste_rate_pct)}</span>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {canWaste && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader title="Mermas por motivo" description={costs ? `Costo total ${formatCOP(waste.data?.total_cost)}` : 'Número de registros'} />
            <div className="px-2 pb-4">
              {waste.isLoading ? <div className="px-3"><Skeleton height={160} /></div> : !reasons.length ? <NoData text="Sin mermas en el período" /> : (
                <ResponsiveContainer width="100%" height={Math.max(150, reasons.length * 38)}>
                  <BarChart data={reasons} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
                    <CartesianGrid horizontal={false} stroke="var(--chart-grid)" />
                    <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} tick={{ ...axisTick, fontSize: 11 }}
                           tickFormatter={costs ? formatCompactNumber : undefined} />
                    <YAxis type="category" dataKey="reason" width={150} tickLine={false} axisLine={false} tick={axisTick} />
                    <Tooltip content={<ChartTooltip money={costs} unit={costs ? undefined : ' registros'} />} cursor={{ fill: 'var(--surface-muted)' }} />
                    <Bar dataKey="value" fill="var(--chart-3)" radius={[0, 4, 4, 0]} maxBarSize={22} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>
          <Card>
            <CardHeader title="Lo que más se pierde" />
            {!waste.data?.by_item.length ? <NoData text="Sin mermas en el período" /> : (
              <ol className="divide-y divide-line border-t border-line">
                {waste.data.by_item.map((r, i) => (
                  <li key={r.item} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                    <span className="w-4 text-ink-subtle num">{i + 1}</span>
                    <span className="flex-1 min-w-0 truncate text-ink">{r.item}</span>
                    <span className="text-xs text-ink-muted num">{formatQty(r.quantity, r.unit)}</span>
                    {r.cost != null && <span className="w-24 text-right font-medium text-ink num">{formatCOP(r.cost)}</span>}
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}

// ── Caja ──────────────────────────────────────────────────────────────────────

export function CashTab({ period }: { period: PeriodQuery }) {
  const { data, isLoading } = useQuery({ queryKey: ['analytics', 'cash', period], queryFn: () => analyticsApi.cash(period) })
  const columns: Column<CashSessionRow>[] = [
    { key: 'register', header: 'Caja', primary: true, cell: (s) => (
      <div><p className="font-medium text-ink">{s.register} · {s.cashier}</p>
        <p className="text-xs text-ink-muted">{formatDateTime(s.opened_at)}{s.closed_at ? ` → ${formatDateTime(s.closed_at)}` : ' · abierta'}</p></div>
    ) },
    { key: 'expected', header: 'Esperado', align: 'right', cell: (s) => (s.expected ? formatCOP(s.expected) : '—') },
    { key: 'counted', header: 'Contado', align: 'right', cell: (s) => (s.counted ? formatCOP(s.counted) : '—') },
    { key: 'difference', header: 'Diferencia', align: 'right', cell: (s) => s.difference === null ? '—' : (
      <span className={cn('font-medium', Number(s.difference) < 0 ? 'text-danger' : Number(s.difference) > 0 ? 'text-warning' : 'text-success')}>
        {Number(s.difference) === 0 ? 'Cuadró' : formatCOP(s.difference)}</span>
    ) },
    { key: 'note', header: 'Nota', hideOnMobile: true, cell: (s) => <span className="text-ink-muted">{s.note || '—'}</span> },
  ]
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Diferencias por cajero" description="Solo cajas cerradas en el período" />
        {isLoading ? <div className="px-5 pb-5"><Skeleton height={80} /></div> : !data?.by_cashier.length ? (
          <EmptyState compact icon={<Wallet size={20} />} title="Sin cierres de caja en el período" />
        ) : (
          <ul className="divide-y divide-line border-t border-line">
            {data.by_cashier.map((c) => (
              <li key={c.cashier} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                <span className="flex-1 min-w-0 truncate text-ink">{c.cashier}</span>
                <span className="text-xs text-ink-muted">{c.sessions} cierre{c.sessions === 1 ? '' : 's'} · {c.with_difference} con diferencia</span>
                <span className={cn('w-28 text-right num font-medium', Number(c.net_difference) < 0 ? 'text-danger' : 'text-ink')}>
                  {formatCOP(c.net_difference)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card>
        <CardHeader title="Aperturas y cierres" actions={<ExportButton run={() => analyticsApi.exportCsv('cash', period)} />} />
        <DataTable caption="Sesiones de caja" columns={columns} rows={data?.sessions} rowKey={(s) => s.id} isLoading={isLoading}
                   empty={<EmptyState compact icon={<Wallet size={20} />} title="No se abrieron cajas en el período" />} />
      </Card>
    </div>
  )
}

// ── Cobertura de ingredientes (dentro de la pestaña Inventario) ───────────────

export function CoverageCard() {
  const { data, isLoading } = useQuery({ queryKey: ['analytics', 'coverage'], queryFn: analyticsApi.coverage })
  return (
    <Card>
      <CardHeader title="¿Para cuántos días alcanza?" description="Existencia ÷ consumo diario promedio de los últimos 30 días (ingredientes)" />
      {isLoading ? <div className="px-5 pb-5"><Skeleton height={120} /></div> : !data?.rows.length ? (
        <NoData text="Aún no hay consumo de ingredientes" description="Aparecerá cuando registres producción o ventas de bebidas preparadas." />
      ) : (
        <ul className="divide-y divide-line border-t border-line">
          {data.rows.slice(0, 12).map((r) => (
            <li key={r.item} className="flex items-center gap-3 px-5 py-2.5 text-sm">
              <span className="flex-1 min-w-0"><span className="block truncate text-ink">{r.name}</span>
                <span className="block text-xs text-ink-muted">Usa {formatQty(r.daily_usage, r.unit)} al día · hay {formatQty(r.stock, r.unit)}</span></span>
              <span className={cn('num font-medium w-24 text-right',
                r.days_left <= 2 ? 'text-danger' : r.days_left <= 7 ? 'text-warning' : 'text-ink')}>
                {r.days_left <= 0 ? 'Agotado' : `${r.days_left.toLocaleString('es-CO', { maximumFractionDigits: 1 })} días`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
