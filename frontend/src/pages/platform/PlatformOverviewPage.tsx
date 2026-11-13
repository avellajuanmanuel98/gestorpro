import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { platformApi, type SubscriptionStatus } from '@/api/platform'
import ChartTooltip from '@/components/charts/ChartTooltip'
import { Card, CardHeader } from '@/components/ui/Card'
import EmptyState from '@/components/ui/EmptyState'
import KpiTile from '@/components/ui/KpiTile'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'
import StatusMark from '@/components/ui/StatusMark'
import { axisTick } from '@/lib/charts'
import { formatDate } from '@/lib/dates'
import { formatCOP } from '@/lib/money'
import { SUBSCRIPTION_STATUS } from '@/lib/status'

const MONTH = new Intl.DateTimeFormat('es-CO', { month: 'short' })
const STATUS_ORDER: SubscriptionStatus[] = ['active', 'trialing', 'trial_expired', 'past_due', 'canceled']

export default function PlatformOverviewPage() {
  const { data, isLoading } = useQuery({ queryKey: ['platform', 'overview'], queryFn: platformApi.overview })
  if (isLoading || !data) {
    return <Page><PageHeader title="Resumen" /><div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {[1, 2, 3, 4].map((i) => <Skeleton key={i} height={96} />)}</div></Page>
  }
  const t = data.tenants
  const subs = data.subscriptions
  const signups = data.signups.map((m) => ({ ...m, label: MONTH.format(new Date(`${m.month}-15`)) }))
  const totalSubs = STATUS_ORDER.reduce((n, k) => n + (subs.by_status[k] ?? 0), 0)
  return (
    <Page>
      <PageHeader title="Resumen de la plataforma"
                  description="Uso de GestorPro por las empresas. Sin montos ni datos de negocio de los clientes." />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiTile label="Empresas activas" value={t.active}
                 hint={`${t.total} en total${t.suspended ? ` · ${t.suspended} suspendida${t.suspended === 1 ? '' : 's'}` : ''}`} />
        <KpiTile label="En uso esta semana" value={t.in_use_7d}
                 hint={t.active ? `${Math.round((t.in_use_7d / t.active) * 100)}% de las activas vendió o registró algo` : 'Sin empresas activas'} />
        <KpiTile label="Nuevas (30 días)" value={t.new_30d} hint={`${data.users} personas con acceso`} />
        <KpiTile label="Ingreso mensual estimado" value={formatCOP(subs.mrr, { compact: true })}
                 hint={subs.active_without_price
                   ? `${subs.active_without_price} activa${subs.active_without_price === 1 ? '' : 's'} sin precio definido`
                   : 'Suma de planes de suscripciones activas'} />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Empresas nuevas por mes" description={`${data.sales_30d.toLocaleString('es-CO')} ventas registradas en la plataforma en los últimos 30 días`} />
          <div className="px-2 pb-4">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={signups} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tick={axisTick} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={32} tick={{ ...axisTick, fontSize: 11 }} />
                <Tooltip content={<ChartTooltip unit=" empresas" />} cursor={{ fill: 'var(--surface-muted)' }} />
                <Bar dataKey="new_tenants" fill="var(--chart-1)" radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <CardHeader title="Suscripciones" />
          <ul className="px-5 pb-5 space-y-3">
            {STATUS_ORDER.map((k) => {
              const n = subs.by_status[k] ?? 0
              return (
                <li key={k}>
                  <div className="flex items-center justify-between text-sm">
                    <StatusMark status={SUBSCRIPTION_STATUS[k]} /><span className="num text-ink">{n}</span>
                  </div>
                  <div className="mt-1 h-1.5 rounded-full bg-surface-muted overflow-hidden" aria-hidden>
                    <div className="h-full rounded-full bg-primary/70" style={{ width: `${totalSubs ? (n / totalSubs) * 100 : 0}%` }} />
                  </div>
                </li>
              )
            })}
            <li className="pt-2 border-t border-line text-xs text-ink-muted">
              {subs.by_plan.map((p) => `${p.name}: ${p.count}`).join(' · ') || 'Sin suscripciones'}
            </li>
          </ul>
        </Card>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader title="Pruebas que terminan esta semana" />
          {!data.trials_ending.length ? <EmptyState compact title="Ninguna prueba termina en los próximos 7 días" /> : (
            <ul className="divide-y divide-line border-t border-line">
              {data.trials_ending.map((r) => (
                <li key={r.id}><Link to={`/platform/tenants/${r.id}`} className="flex items-center gap-3 px-5 py-2.5 text-sm hover:bg-surface-muted/60">
                  <span className="flex-1 truncate text-ink">{r.name}</span>
                  <span className="text-xs text-ink-muted">termina el {formatDate(r.trial_ends_at)}</span>
                  <ArrowRight size={14} className="text-ink-subtle" /></Link></li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <CardHeader title="Requieren gestión" description="Prueba vencida o pago pendiente" />
          {!data.attention.length ? <EmptyState compact title="Todo al día" /> : (
            <ul className="divide-y divide-line border-t border-line">
              {data.attention.map((r) => (
                <li key={r.id}><Link to={`/platform/tenants/${r.id}`} className="flex items-center gap-3 px-5 py-2.5 text-sm hover:bg-surface-muted/60">
                  <span className="flex-1 truncate text-ink">{r.name}</span>
                  <StatusMark status={SUBSCRIPTION_STATUS[r.kind]} />
                  <ArrowRight size={14} className="text-ink-subtle" /></Link></li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </Page>
  )
}
