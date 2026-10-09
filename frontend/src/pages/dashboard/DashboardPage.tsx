import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowRight, BarChart2, CircleDollarSign, PackageX } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { billingApi } from '@/api/billing'
import { customersApi } from '@/api/customers'
import { catalogApi } from '@/api/catalog'
import { formatQty } from '@/lib/catalog'
import { Card, CardHeader } from '@/components/ui/Card'
import EmptyState from '@/components/ui/EmptyState'
import KpiTile from '@/components/ui/KpiTile'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatCOP, formatCompactNumber, toDisplayNumber } from '@/lib/money'
import { INVOICE_STATUS } from '@/lib/status'
import { useAuthStore, useCan } from '@/store/authStore'
import { LifecycleMark } from '@/components/ui/StatusMark'

interface ChartTooltipProps { active?: boolean; label?: string; payload?: { value: number }[] }

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface border border-line rounded-lg shadow-overlay px-3 py-2 text-sm">
      <p className="text-xs text-ink-muted">{label}</p>
      <p className="font-semibold text-ink num">{formatCOP(payload[0].value)}</p>
    </div>
  )
}

function AttentionItem({ icon: Icon, tone, title, detail, to }: {
  icon: React.ElementType; tone: 'danger' | 'warning' | 'info'; title: string; detail: string; to: string
}) {
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

export default function DashboardPage() {
  const can = useCan()
  const tenantName = useAuthStore((s) => s.session?.tenant?.name)
  // Sin permiso NO se consulta: mostrar ceros sería mostrar datos inventados.
  const canReports = can('reports.view')
  const canBilling = can('billing.view')
  const canCustomers = can('customers.view')
  const canCatalog = can('catalog.view')

  const summary = useQuery({ queryKey: ['billing-summary'], queryFn: billingApi.summary, enabled: canReports })
  const monthly = useQuery({ queryKey: ['monthly-revenue'], queryFn: billingApi.monthlyRevenue, enabled: canReports })
  const recent = useQuery({ queryKey: ['recent-invoices'], queryFn: billingApi.recent, enabled: canBilling })
  const customers = useQuery({
    queryKey: ['customers', 'active-count'], queryFn: () => customersApi.list({ status: 'active', exclude_final_consumer: true, page_size: 1 }),
    enabled: canCustomers,
  })
  const lowStock = useQuery({ queryKey: ['low-stock'], queryFn: () => catalogApi.lowStock({ page_size: 5 }), enabled: canCatalog })

  const chartData = (monthly.data ?? []).map((m) => ({ ...m, total: toDisplayNumber(m.total) }))
  const hasRevenue = chartData.some((m) => m.total > 0)
  const overdue = summary.data?.overdue_count ?? 0
  const pending = toDisplayNumber(summary.data?.pending_total)
  const low = lowStock.data?.count ?? 0

  const attention = [
    canReports && overdue > 0 && { icon: AlertTriangle, tone: 'danger' as const, to: '/invoices',
      title: `${overdue} factura${overdue === 1 ? '' : 's'} vencida${overdue === 1 ? '' : 's'}`, detail: 'Gestiona el cobro o actualiza su estado' },
    canCatalog && low > 0 && { icon: PackageX, tone: 'warning' as const,
      to: lowStock.data?.results.every((i) => i.kind === 'raw_material') ? '/ingredients' : '/inventory',
      title: `${low} ${low === 1 ? 'ítem' : 'ítems'} bajo el mínimo`,
      detail: lowStock.data?.results.slice(0, 3).map((i) => `${i.name} (${formatQty(i.stock, i.unit_symbol)})`).join(', ') ?? '' },
    canReports && pending > 0 && { icon: CircleDollarSign, tone: 'info' as const, to: '/invoices',
      title: `${formatCOP(pending, { compact: true })} por cobrar`, detail: 'Facturas en borrador, enviadas o vencidas' },
  ].filter(Boolean) as Parameters<typeof AttentionItem>[0][]

  const attentionLoading = (canReports && summary.isLoading) || (canCatalog && lowStock.isLoading)

  return (
    <Page>
      <PageHeader title="Inicio" description={tenantName} />

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <KpiTile label="Total recaudado" loading={summary.isLoading && canReports}
                 unavailable={canReports ? undefined : 'No incluido en tu rol'}
                 value={formatCOP(summary.data?.paid_total, { compact: true })}
                 hint="Facturas pagadas" />
        <KpiTile label="Por cobrar" loading={summary.isLoading && canReports}
                 unavailable={canReports ? undefined : 'No incluido en tu rol'}
                 value={formatCOP(summary.data?.pending_total, { compact: true })}
                 hint={`${summary.data?.total_invoices ?? 0} facturas emitidas`} />
        <KpiTile label="Facturas vencidas" loading={summary.isLoading && canReports}
                 unavailable={canReports ? undefined : 'No incluido en tu rol'}
                 value={overdue} tone={overdue > 0 ? 'danger' : 'default'}
                 hint={overdue > 0 ? 'Requieren seguimiento' : 'Todo al día'} />
        <KpiTile label="Clientes activos" loading={customers.isLoading && canCustomers}
                 unavailable={canCustomers ? undefined : 'No incluido en tu rol'}
                 value={customers.data?.count ?? 0} hint="Con estado activo" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Ingresos por mes" description="Facturas pagadas · últimos 6 meses" />
          <div className="px-2 pb-4">
            {!canReports ? (
              <EmptyState compact icon={<BarChart2 size={20} />} title="No incluido en tu rol" />
            ) : monthly.isLoading ? (
              <div className="px-3"><Skeleton height={220} /></div>
            ) : !hasRevenue ? (
              <EmptyState compact icon={<BarChart2 size={20} />} title="Aún no hay ingresos registrados"
                          description="Aparecerán cuando marques facturas como pagadas." />
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
                  <XAxis dataKey="mes" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: 'var(--ink-muted)' }} />
                  <YAxis tickLine={false} axisLine={false} width={56} tick={{ fontSize: 11, fill: 'var(--ink-subtle)' }}
                         tickFormatter={(v) => formatCompactNumber(v)} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--surface-muted)' }} />
                  <Bar dataKey="total" fill="var(--chart-1)" radius={[4, 4, 0, 0]} maxBarSize={44} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Requiere atención" />
          {attentionLoading ? (
            <div className="px-5 pb-5 space-y-3"><Skeleton height={36} /><Skeleton height={36} /></div>
          ) : attention.length === 0 ? (
            <EmptyState compact title="Nada pendiente" description="No hay facturas vencidas ni productos bajo el mínimo." />
          ) : (
            <ul className="divide-y divide-line border-t border-line">
              {attention.map((item) => <AttentionItem key={item.title} {...item} />)}
            </ul>
          )}
        </Card>
      </div>

      {canBilling && (
        <Card>
          <CardHeader title="Documentos recientes"
                      actions={<Link to="/invoices" className="text-xs font-medium text-primary-ink hover:underline">Ver todos</Link>} />
          {recent.isLoading ? (
            <div className="px-5 pb-5 space-y-3"><Skeleton height={20} /><Skeleton height={20} /></div>
          ) : !recent.data?.length ? (
            <EmptyState compact title="Aún no hay documentos" description="Las facturas y cotizaciones aparecerán aquí." />
          ) : (
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
          )}
        </Card>
      )}
    </Page>
  )
}
