import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowRight, BarChart2, CircleDollarSign, Clock, PackageX, TrendingDown, Wallet } from 'lucide-react'
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { analyticsApi, type AttentionItem as ApiAttention, type PeriodInfo, type ProductRow } from '@/api/analytics'
import { billingApi } from '@/api/billing'
import Delta from '@/components/analytics/Delta'
import PeriodPicker from '@/components/analytics/PeriodPicker'
import { isReady, usePeriod } from '@/lib/period'
import QuadrantMark from '@/components/analytics/QuadrantMark'
import { Card, CardHeader } from '@/components/ui/Card'
import EmptyState from '@/components/ui/EmptyState'
import KpiTile from '@/components/ui/KpiTile'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'
import { LifecycleMark } from '@/components/ui/StatusMark'
import { formatQty } from '@/lib/catalog'
import { cn } from '@/lib/cn'
import { formatTime } from '@/lib/dates'
import { formatCOP, formatCompactNumber, toDisplayNumber } from '@/lib/money'
import { INVOICE_STATUS } from '@/lib/status'
import { useAuthStore, useCan } from '@/store/authStore'

interface HourTooltipProps { active?: boolean; label?: number; payload?: { dataKey: string; value: number }[]; previous?: string }

function HourTooltip({ active, payload, label, previous }: HourTooltipProps) {
  if (!active || !payload?.length) return null
  const cur = payload.find((p) => p.dataKey === 'sales')?.value ?? 0
  const prev = payload.find((p) => p.dataKey === 'previous')?.value ?? 0
  return (
    <div className="bg-surface border border-line rounded-lg shadow-overlay px-3 py-2 text-sm">
      <p className="text-xs text-ink-muted">{label}:00 – {label}:59</p>
      <p className="font-semibold text-ink num">{formatCOP(cur)}</p>
      <p className="text-xs text-ink-muted num">{previous}: {formatCOP(prev)}</p>
    </div>
  )
}

type Tone = 'danger' | 'warning' | 'info'
interface AttentionEntry { icon: React.ElementType; tone: Tone; title: string; detail: string; to: string }

const ATTENTION_COPY: Record<ApiAttention['kind'], { icon: React.ElementType; title: (n: number) => string }> = {
  negative_stock: { icon: TrendingDown, title: (n) => `${n} ${n === 1 ? 'ítem' : 'ítems'} con existencia negativa` },
  low_stock: { icon: PackageX, title: (n) => `${n} ${n === 1 ? 'ítem' : 'ítems'} bajo el mínimo` },
  stale_cash: { icon: Clock, title: (n) => `${n} ${n === 1 ? 'caja abierta' : 'cajas abiertas'} hace más de 12 horas` },
}

function AttentionRow({ icon: Icon, tone, title, detail, to }: AttentionEntry) {
  const tones = { danger: 'bg-danger-soft text-danger', warning: 'bg-warning-soft text-warning', info: 'bg-info-soft text-info' }
  return (
    <li>
      <Link to={to} className="flex items-center gap-3 px-5 py-3 hover:bg-surface-muted/60 transition-colors group">
        <span className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${tones[tone]}`}><Icon size={16} /></span>
        <span className="flex-1 min-w-0">
          <span className="block text-sm font-medium text-ink">{title}</span>
          <span className="block text-xs text-ink-muted truncate">{detail}</span>
        </span>
        <ArrowRight size={14} className="text-ink-subtle group-hover:text-ink shrink-0" />
      </Link>
    </li>
  )
}

/** Lista corta con barra proporcional: la longitud se lee más rápido que el número. */
function RankList({ rows, value, render, empty }: {
  rows: ProductRow[]; value: (r: ProductRow) => number; render: (r: ProductRow) => React.ReactNode; empty: string
}) {
  if (!rows.length) return <EmptyState compact icon={<BarChart2 size={20} />} title={empty} />
  const max = Math.max(...rows.map(value), 1)
  return (
    <ol className="divide-y divide-line border-t border-line">
      {rows.map((r, i) => (
        <li key={r.item} className="px-5 py-2.5">
          <div className="flex items-center gap-3 text-sm">
            <span className="w-4 text-ink-subtle num">{i + 1}</span>
            <span className="flex-1 min-w-0 truncate text-ink">{r.name}</span>
            {render(r)}
          </div>
          <div className="ml-7 mt-1 h-1 rounded-full bg-surface-muted overflow-hidden" aria-hidden>
            <div className="h-full rounded-full bg-primary/70" style={{ width: `${Math.max(2, (value(r) / max) * 100)}%` }} />
          </div>
        </li>
      ))}
    </ol>
  )
}

const periodNoun = (p?: PeriodInfo) => (p?.preset === 'today' ? 'hoy' : p?.preset === 'yesterday' ? 'ayer' : 'del período')

export default function DashboardPage() {
  const can = useCan()
  const tenantName = useAuthStore((s) => s.session?.tenant?.name)
  // Sin permiso NO se consulta: mostrar ceros sería mostrar datos inventados.
  const canReports = can('reports.view')
  const canBilling = can('billing.view')
  const canCash = can('cash.manage')
  const showCosts = can('catalog.view_costs')
  const [period, setPeriod] = usePeriod('today')
  const ready = canReports && isReady(period)

  const summary = useQuery({ queryKey: ['analytics', 'summary', period], queryFn: () => analyticsApi.summary(period), enabled: ready })
  const hourly = useQuery({ queryKey: ['analytics', 'hourly', period], queryFn: () => analyticsApi.hourly(period), enabled: ready })
  const products = useQuery({ queryKey: ['analytics', 'products', period], queryFn: () => analyticsApi.products(period), enabled: ready })
  const cash = useQuery({ queryKey: ['analytics', 'cash', period], queryFn: () => analyticsApi.cash(period), enabled: ready && canCash })
  const billing = useQuery({ queryKey: ['billing-summary'], queryFn: billingApi.summary, enabled: canReports })
  const recent = useQuery({ queryKey: ['recent-invoices'], queryFn: billingApi.recent, enabled: canBilling })

  const info = summary.data?.period
  const k = summary.data?.kpis
  const loading = summary.isLoading && ready
  const unavailable = canReports ? undefined : 'No incluido en tu rol'

  const overdue = billing.data?.overdue_count ?? 0
  const pending = toDisplayNumber(billing.data?.pending_total)
  const attention: AttentionEntry[] = [
    ...(summary.data?.attention ?? []).map((a) => ({
      icon: ATTENTION_COPY[a.kind].icon, tone: a.tone, title: ATTENTION_COPY[a.kind].title(a.count), detail: a.detail, to: a.to,
    })),
    ...(overdue > 0 ? [{ icon: AlertTriangle, tone: 'danger' as const, to: '/invoices', detail: 'Gestiona el cobro o actualiza su estado',
      title: `${overdue} factura${overdue === 1 ? '' : 's'} vencida${overdue === 1 ? '' : 's'}` }] : []),
    ...(pending > 0 ? [{ icon: CircleDollarSign, tone: 'info' as const, to: '/invoices', detail: 'Facturas en borrador, enviadas o vencidas',
      title: `${formatCOP(pending, { compact: true })} por cobrar` }] : []),
  ]

  const hours = (hourly.data?.hours ?? []).map((h) => ({ hour: h.hour, sales: toDisplayNumber(h.sales), previous: toDisplayNumber(h.previous_sales) }))
  const hasHourly = hours.some((h) => h.sales > 0 || h.previous > 0)
  const multiDay = (info?.days ?? 1) > 1
  const rows = products.data?.rows ?? []
  const topSellers = rows.filter((r) => Number(r.units) > 0).slice(0, 5)
  const topProfit = [...rows].filter((r) => Number(r.gross_profit ?? 0) > 0)
    .sort((a, b) => Number(b.gross_profit) - Number(a.gross_profit)).slice(0, 5)
  const openSessions = cash.data?.sessions.filter((s) => s.status === 'open') ?? []
  const closedWithDiff = cash.data?.sessions.filter((s) => s.difference !== null && Number(s.difference) !== 0) ?? []

  return (
    <Page>
      <PageHeader title="Inicio" description={tenantName} />
      {canReports && <PeriodPicker value={period} onChange={setPeriod} presets={['today', 'yesterday', '7d', '30d', 'this_month', 'last_month']} info={info} />}

      <div className={cn('grid grid-cols-2 gap-3', showCosts ? 'lg:grid-cols-5' : 'lg:grid-cols-3')}>
        <KpiTile label={`Ventas ${periodNoun(info)}`} loading={loading} unavailable={unavailable}
                 value={formatCOP(k?.sales.value, { compact: true })}
                 hint={k && <Delta pct={k.sales.change_pct} />} />
        <KpiTile label="Transacciones" loading={loading} unavailable={unavailable} value={k?.transactions.value ?? 0}
                 hint={k && <Delta pct={k.transactions.change_pct} />} />
        <KpiTile label="Ticket promedio" loading={loading} unavailable={unavailable}
                 value={k?.average_ticket.value ? formatCOP(k.average_ticket.value) : '—'}
                 hint={k && (k.average_ticket.value ? <Delta pct={k.average_ticket.change_pct} /> : 'Sin ventas en el período')} />
        {showCosts && (
          <>
            <KpiTile label="Utilidad bruta" loading={loading} unavailable={unavailable}
                     value={formatCOP(k?.gross_profit?.value, { compact: true })}
                     hint={k && <span className="flex flex-col gap-0.5">
                       {k.gross_margin_pct != null && <span>Margen {k.gross_margin_pct.toLocaleString('es-CO')}% sobre ventas sin IVA</span>}
                       <Delta pct={k.gross_profit?.change_pct} />
                     </span>} />
            <KpiTile label="Mermas (a costo)" loading={loading} unavailable={unavailable}
                     tone={Number(k?.waste_cost?.value ?? 0) > 0 ? 'warning' : 'default'}
                     value={formatCOP(k?.waste_cost?.value, { compact: true })}
                     hint={k && <span className="flex flex-col gap-0.5">
                       {k.waste_pct_of_cost != null && <span>{k.waste_pct_of_cost.toLocaleString('es-CO')}% de lo que salió a costo</span>}
                       <Delta pct={k.waste_cost?.change_pct} inverse />
                     </span>} />
          </>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Ventas por hora"
                      description={info && <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1">
                        {multiDay && <span>Promedio por día.</span>}
                        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: 'var(--chart-1)' }} />{info.label}</span>
                        <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-3 rounded" style={{ background: 'var(--ink-subtle)' }} />{info.previous.label}</span>
                      </span>} />
          <div className="px-2 pb-4">
            {!canReports ? (
              <EmptyState compact icon={<BarChart2 size={20} />} title="No incluido en tu rol" />
            ) : hourly.isLoading ? (
              <div className="px-3"><Skeleton height={220} /></div>
            ) : !hasHourly ? (
              <EmptyState compact icon={<BarChart2 size={20} />} title="Aún no hay ventas en este período"
                          description="Las ventas del POS aparecerán aquí, hora por hora." />
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart data={hours} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
                  <XAxis dataKey="hour" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: 'var(--ink-muted)' }}
                         tickFormatter={(h: number) => `${h}h`} />
                  <YAxis tickLine={false} axisLine={false} width={56} tick={{ fontSize: 11, fill: 'var(--ink-subtle)' }}
                         tickFormatter={(v) => formatCompactNumber(v)} />
                  <Tooltip content={<HourTooltip previous={info?.previous.label} />} cursor={{ fill: 'var(--surface-muted)' }} />
                  <Bar dataKey="sales" fill="var(--chart-1)" radius={[4, 4, 0, 0]} maxBarSize={28} />
                  <Line dataKey="previous" type="monotone" stroke="var(--ink-subtle)" strokeWidth={1.5} strokeDasharray="4 3" dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Requiere atención" />
          {canReports && (summary.isLoading || billing.isLoading) ? (
            <div className="px-5 pb-5 space-y-3"><Skeleton height={36} /><Skeleton height={36} /></div>
          ) : attention.length === 0 ? (
            <EmptyState compact title="Nada pendiente" description="Existencias sobre el mínimo, cajas al día y sin facturas vencidas." />
          ) : (
            <ul className="divide-y divide-line border-t border-line">
              {attention.map((item) => <AttentionRow key={item.title} {...item} />)}
            </ul>
          )}
        </Card>
      </div>

      {canReports && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader title="Más vendidos" description="Por ingreso sin IVA"
                        actions={<Link to={`/reports?tab=profit&period=${period.period}`} className="text-xs font-medium text-primary-ink hover:underline">Ver todo</Link>} />
            {products.isLoading ? <div className="px-5 pb-5"><Skeleton height={160} /></div> : (
              <RankList rows={topSellers} value={(r) => Number(r.revenue)} empty="Sin ventas en el período"
                        render={(r) => <span className="text-right num"><span className="text-xs text-ink-muted mr-2">{formatQty(r.units, r.unit)}</span>
                          <span className="font-medium text-ink">{formatCOP(r.revenue)}</span></span>} />
            )}
          </Card>
          {showCosts && (
            <Card>
              <CardHeader title="Los que más dejan" description="Utilidad bruta: ingreso sin IVA − costo" />
              {products.isLoading ? <div className="px-5 pb-5"><Skeleton height={160} /></div> : (
                <RankList rows={topProfit} value={(r) => Number(r.gross_profit)} empty="Sin utilidad registrada en el período"
                          render={(r) => <span className="flex items-center gap-3">
                            {r.quadrant && <QuadrantMark quadrant={r.quadrant} label={r.quadrant_label} advice={r.quadrant_advice} showLabel={false} />}
                            {r.margin_pct != null && <span className="text-xs text-ink-muted num">{r.margin_pct.toLocaleString('es-CO')}%</span>}
                            <span className="font-medium text-ink num">{formatCOP(r.gross_profit)}</span>
                          </span>} />
              )}
            </Card>
          )}
        </div>
      )}

      {canReports && canCash && (
        <Card>
          <CardHeader title="Caja" description={info?.label}
                      actions={<Link to="/cash" className="text-xs font-medium text-primary-ink hover:underline">Ir a caja</Link>} />
          {cash.isLoading ? <div className="px-5 pb-5"><Skeleton height={60} /></div> : !cash.data?.sessions.length ? (
            <EmptyState compact icon={<Wallet size={20} />} title="No se abrieron cajas en este período" />
          ) : (
            <ul className="divide-y divide-line border-t border-line">
              {[...openSessions, ...closedWithDiff].slice(0, 5).map((s) => (
                <li key={s.id} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                  <span className={cn('w-2 h-2 rounded-full shrink-0', s.status === 'open' ? 'bg-success' : 'bg-warning')} aria-hidden />
                  <span className="flex-1 min-w-0 truncate text-ink">{s.register} · {s.cashier}</span>
                  {s.status === 'open'
                    ? <span className="text-xs text-ink-muted">Abierta desde {formatTime(s.opened_at)}</span>
                    : <span className={cn('num font-medium', Number(s.difference) < 0 ? 'text-danger' : 'text-warning')}>
                        {Number(s.difference) > 0 ? 'Sobrante ' : 'Faltante '}{formatCOP(Math.abs(Number(s.difference)))}</span>}
                </li>
              ))}
              {!openSessions.length && !closedWithDiff.length && (
                <li className="px-5 py-3 text-sm text-ink-muted">{cash.data.sessions.length} cierre{cash.data.sessions.length === 1 ? '' : 's'} sin diferencias.</li>
              )}
            </ul>
          )}
        </Card>
      )}

      {canBilling && !!recent.data?.length && (
        <Card>
          <CardHeader title="Documentos recientes"
                      actions={<Link to="/invoices" className="text-xs font-medium text-primary-ink hover:underline">Ver todos</Link>} />
          <ul className="divide-y divide-line border-t border-line">
            {recent.data.map((inv) => (
              <li key={inv.id} className="flex items-center gap-4 px-5 py-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink">{inv.number}</p>
                  <p className="text-xs text-ink-muted truncate">{inv.customer}</p>
                </div>
                <LifecycleMark status={INVOICE_STATUS[inv.status]} />
                <span className="text-sm font-medium text-ink num w-28 text-right">{formatCOP(inv.total)}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </Page>
  )
}
