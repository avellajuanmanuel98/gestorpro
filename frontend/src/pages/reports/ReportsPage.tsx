import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, BarChart2 } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { analyticsApi } from '@/api/analytics'
import { reportsApi } from '@/api/reports'
import ChartTooltip from '@/components/charts/ChartTooltip'
import { axisTick, CHART_COLORS } from '@/lib/charts'
import { Card, CardHeader } from '@/components/ui/Card'
import EmptyState from '@/components/ui/EmptyState'
import KpiTile from '@/components/ui/KpiTile'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'
import Tabs from '@/components/ui/Tabs'
import { formatQty } from '@/lib/catalog'
import { formatCOP, formatCompactNumber, toDisplayNumber } from '@/lib/money'
import { INVOICE_STATUS } from '@/lib/status'
import { useAuthStore, useCan, useHasFeature } from '@/store/authStore'
import PeriodPicker from '@/components/analytics/PeriodPicker'
import { isReady, usePeriod } from '@/lib/period'
import { CashTab, CoverageCard, ProductionWasteTab, ProfitTab, SalesTab } from './AnalyticsTabs'
import type { Invoice } from '@/types'
import { LifecycleMark } from '@/components/ui/StatusMark'

const Loading = () => <div className="grid gap-4 md:grid-cols-2"><Skeleton height={280} /><Skeleton height={280} /></div>
const NoData = ({ text }: { text: string }) => <EmptyState compact icon={<BarChart2 size={20} />} title={text} />

function BillingTab() {
  const { data, isLoading } = useQuery({ queryKey: ['report-billing'], queryFn: reportsApi.billing })
  if (isLoading || !data) return <Loading />
  const trend = data.monthly_trend.map((m) => ({ ...m, total: toDisplayNumber(m.total) }))
  const hasSales = trend.some((m) => m.total > 0)
  const statusTotal = data.status_breakdown.reduce((s, r) => s + r.count, 0)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Ventas facturadas por mes" description="Facturas pagadas · últimos 12 meses" />
        <div className="px-2 pb-4">
          {!hasSales ? <NoData text="Aún no hay ventas pagadas" /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={trend} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
                <XAxis dataKey="mes" tickLine={false} axisLine={false} tick={axisTick} />
                <YAxis tickLine={false} axisLine={false} width={56} tick={{ ...axisTick, fontSize: 11 }} tickFormatter={formatCompactNumber} />
                <Tooltip content={<ChartTooltip money />} cursor={{ fill: 'var(--surface-muted)' }} />
                <Bar dataKey="total" fill="var(--chart-1)" radius={[4, 4, 0, 0]} maxBarSize={36} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader title="Facturas por estado" />
          {!statusTotal ? <NoData text="Aún no hay facturas" /> : (
            <ul className="px-5 pb-5 space-y-3">
              {data.status_breakdown.map((r) => {
                const meta = INVOICE_STATUS[r.status as Invoice['status']]
                const pct = Math.round((r.count / statusTotal) * 100)
                return (
                  <li key={r.status}>
                    <div className="flex justify-between text-sm">{meta ? <LifecycleMark status={meta} /> : <span className="text-ink">{r.label}</span>}
                      <span className="text-ink-muted num">{r.count} · {formatCOP(r.total, { compact: true })}</span></div>
                    <div className="mt-1 h-1.5 rounded-full bg-surface-muted overflow-hidden" aria-hidden>
                      <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
        <Card>
          <CardHeader title="Clientes con más compras" description="Por facturas pagadas" />
          {!data.top_clients.length ? <NoData text="Aún no hay clientes con pagos" /> : (
            <ol className="divide-y divide-line border-t border-line">
              {data.top_clients.map((c, i) => (
                <li key={`${c.name}-${i}`} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                  <span className="w-5 text-ink-subtle num">{i + 1}</span>
                  <span className="flex-1 min-w-0 truncate text-ink">{c.name}</span>
                  <span className="text-xs text-ink-muted num">{c.count} fact.</span>
                  <span className="w-28 text-right font-medium text-ink num">{formatCOP(c.total)}</span>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>
    </div>
  )
}

function InventoryTab() {
  const { data, isLoading } = useQuery({ queryKey: ['report-inventory'], queryFn: reportsApi.inventory })
  if (isLoading || !data) return <Loading />
  const showCosts = data.valor_inventario !== null
  const chart = data.by_category.map((r) => ({ ...r, valor: toDisplayNumber(r.valor) }))
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiTile label="Productos activos" value={data.total_productos} />
        <KpiTile label="Ingredientes activos" value={data.total_ingredientes} />
        <KpiTile label="Inventario de ingredientes" unavailable={showCosts ? undefined : 'No incluido en tu rol'}
                 value={formatCOP(data.valor_ingredientes, { compact: true })} hint="A costo: existencia × costo por unidad." />
        <KpiTile label="Inventario de productos" unavailable={showCosts ? undefined : 'No incluido en tu rol'}
                 value={formatCOP(data.valor_productos, { compact: true })} hint="A costo, no a precio de venta." />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader title={showCosts ? 'Valor del inventario por categoría' : 'Ítems por categoría'}
                      description={<span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1">
                        {showCosts && <span>A costo.</span>}
                        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: 'var(--chart-2)' }} />Ingredientes</span>
                        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: 'var(--chart-1)' }} />Productos</span>
                      </span>} />
          <div className="px-2 pb-4">
            {!chart.length ? <NoData text="Aún no hay productos ni ingredientes" /> : (
              <ResponsiveContainer width="100%" height={Math.max(160, chart.length * 38)}>
                <BarChart data={chart} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
                  <CartesianGrid horizontal={false} stroke="var(--chart-grid)" />
                  <XAxis type="number" tickLine={false} axisLine={false} tick={{ ...axisTick, fontSize: 11 }}
                         tickFormatter={showCosts ? (v: number) => formatCOP(v, { compact: true }) : undefined} />
                  <YAxis type="category" dataKey="categoria" width={140} tickLine={false} axisLine={false} tick={axisTick} />
                  <Tooltip content={<ChartTooltip money={showCosts} unit={showCosts ? undefined : ' ítems'} />}
                           cursor={{ fill: 'var(--surface-muted)' }} />
                  <Bar dataKey={showCosts ? 'valor' : 'items'} name={showCosts ? 'Valor' : 'Ítems'} radius={[0, 4, 4, 0]} maxBarSize={22}>
                    {chart.map((r) => <Cell key={`${r.grupo}-${r.categoria}`} fill={r.grupo === 'ingredientes' ? 'var(--chart-2)' : 'var(--chart-1)'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title="Bajo el mínimo" description="Productos e ingredientes en su mínimo o por debajo" />
          {!data.low_stock.length ? <NoData text="Todo está sobre el mínimo" /> : (
            <ul className="divide-y divide-line border-t border-line">
              {data.low_stock.map((p) => (
                <li key={p.id} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                  <AlertTriangle size={14} className="text-warning shrink-0" />
                  <span className="flex-1 min-w-0"><span className="block truncate text-ink">{p.name}</span>
                    <span className="block text-xs text-ink-muted">{p.code}</span></span>
                  <span className="text-right num"><span className={Number(p.stock) === 0 ? 'text-danger font-medium' : 'text-warning font-medium'}>
                    {formatQty(p.stock, p.unit)}</span>
                    <span className="text-ink-subtle"> / mín. {formatQty(p.minimum_stock)}</span></span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}

function TeamTab() {
  const { data, isLoading } = useQuery({ queryKey: ['report-hr'], queryFn: reportsApi.hr })
  if (isLoading || !data) return <Loading />
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <KpiTile label="Personal activo" value={data.employees_active} />
        <KpiTile label="Personal inactivo" value={data.employees_inactive} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader title="Personal por área" />
          <div className="px-2 pb-4">
            {!data.by_department.length ? <NoData text="Sin fichas de personal" /> : (
              <ResponsiveContainer width="100%" height={Math.max(160, data.by_department.length * 38)}>
                <BarChart data={data.by_department} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
                  <CartesianGrid horizontal={false} stroke="var(--chart-grid)" />
                  <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} tick={{ ...axisTick, fontSize: 11 }} />
                  <YAxis type="category" dataKey="departamento" width={120} tickLine={false} axisLine={false} tick={axisTick} />
                  <Tooltip content={<ChartTooltip unit=" personas" />} cursor={{ fill: 'var(--surface-muted)' }} />
                  <Bar dataKey="total" radius={[0, 4, 4, 0]} maxBarSize={22}>
                    {data.by_department.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title="Proveedores por categoría" />
          {!data.suppliers_by_category.length ? <NoData text="Sin proveedores" /> : (
            <ul className="divide-y divide-line border-t border-line">
              {data.suppliers_by_category.map((s) => (
                <li key={s.categoria} className="flex justify-between px-5 py-2.5 text-sm">
                  <span className="text-ink">{s.categoria}</span><span className="text-ink-muted num">{s.total}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}

type TabId = 'sales' | 'profit' | 'production' | 'inventory' | 'cash' | 'billing' | 'team'
const PERIOD_TABS: TabId[] = ['sales', 'profit', 'production', 'cash']

export default function ReportsPage() {
  const can = useCan()
  const hasHr = useHasFeature()('module.hr') && can('hr.view')
  const isBakery = useAuthStore((s) => s.session?.tenant?.vertical) === 'bakery'
  const [params, setParams] = useSearchParams()
  const [period, setPeriod] = usePeriod('7d')
  const tabs: { id: TabId; label: string }[] = [
    { id: 'sales', label: 'Ventas' },
    { id: 'profit', label: 'Rentabilidad' },
    { id: 'production', label: isBakery ? 'Producción y mermas' : 'Mermas' },
    { id: 'inventory', label: 'Inventario' },
    ...(can('cash.manage') ? [{ id: 'cash' as const, label: 'Caja' }] : []),
    { id: 'billing', label: 'Facturación' },
    ...(hasHr ? [{ id: 'team' as const, label: 'Equipo y proveedores' }] : []),
  ]
  const requested = params.get('tab') as TabId | null
  const tab = tabs.find((t) => t.id === requested)?.id ?? 'sales'
  const setTab = (id: TabId) => setParams((prev) => { const next = new URLSearchParams(prev); next.set('tab', id); return next }, { replace: true })
  const withPeriod = PERIOD_TABS.includes(tab)
  const summary = useQuery({ queryKey: ['analytics', 'summary', period], queryFn: () => analyticsApi.summary(period),
                             enabled: withPeriod && isReady(period) })
  return (
    <Page>
      <PageHeader title="Reportes" description="Cifras calculadas con los datos reales de tu empresa" />
      <Tabs label="Reportes" tabs={tabs} value={tab} onChange={setTab} />
      {withPeriod && <PeriodPicker value={period} onChange={setPeriod} info={summary.data?.period} />}
      {withPeriod && !isReady(period) && <EmptyState compact title="Elige las dos fechas del rango" />}
      {withPeriod && isReady(period) && (
        <>
          {tab === 'sales' && <SalesTab period={period} />}
          {tab === 'profit' && <ProfitTab period={period} />}
          {tab === 'production' && <ProductionWasteTab period={period} canWaste={can('waste.view')} />}
          {tab === 'cash' && <CashTab period={period} />}
        </>
      )}
      {tab === 'inventory' && <div className="space-y-4"><InventoryTab />{can('inventory.view') && <CoverageCard />}</div>}
      {tab === 'billing' && <BillingTab />}
      {tab === 'team' && hasHr && <TeamTab />}
    </Page>
  )
}
