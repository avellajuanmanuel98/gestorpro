import { useQuery } from '@tanstack/react-query'
import {
  Users, FileText, TrendingUp, AlertTriangle,
  ArrowUpRight, ArrowDownRight, Minus,
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { billingApi } from '@/api/billing'
import { clientsApi } from '@/api/clients'
import Badge from '@/components/ui/Badge'
import { SkeletonCard } from '@/components/ui/Skeleton'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCurrency(value: number) {
  return new Intl.NumberFormat('es-CO', {
    style:                 'currency',
    currency:              'COP',
    minimumFractionDigits: 0,
    notation:              value >= 1_000_000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 1_000_000 ? 1 : 0,
  }).format(value)
}

const STATUS_MAP: Record<string, { label: string; variant: 'default' | 'info' | 'success' | 'danger' | 'warning' }> = {
  draft:     { label: 'Borrador',  variant: 'default'  },
  sent:      { label: 'Enviada',   variant: 'info'     },
  paid:      { label: 'Pagada',    variant: 'success'  },
  overdue:   { label: 'Vencida',   variant: 'danger'   },
  cancelled: { label: 'Cancelada', variant: 'default'  },
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

interface StatCardProps {
  title:       string
  value:       string | number
  icon:        React.ElementType
  trend?:      number   // percentage change, positive = up, negative = down
  colorClass:  string   // Tailwind color class for icon bg
  glowClass:   string   // Custom glow class
  delay?:      string
}

function StatCard({ title, value, icon: Icon, trend, colorClass, glowClass, delay = '' }: StatCardProps) {
  const TrendIcon = trend == null ? null : trend > 0 ? ArrowUpRight : trend < 0 ? ArrowDownRight : Minus
  const trendColor =
    trend == null ? '' :
    trend > 0  ? 'text-emerald-600 dark:text-emerald-400' :
    trend < 0  ? 'text-red-500 dark:text-red-400' :
                 'text-zinc-400'

  return (
    <div
      className={[
        'animate-fade-up',
        'relative bg-white dark:bg-zinc-900',
        'border border-zinc-200 dark:border-zinc-800',
        'rounded-2xl p-5 overflow-hidden',
        'transition-all duration-200 hover:-translate-y-0.5',
        glowClass,
        delay,
      ].filter(Boolean).join(' ')}
    >
      {/* Subtle background glow */}
      <div className={['absolute -top-6 -right-6 w-24 h-24 rounded-full opacity-[0.06] blur-2xl', colorClass].join(' ')} />

      <div className="relative flex items-start justify-between">
        {/* Icon */}
        <div className={['w-10 h-10 rounded-xl flex items-center justify-center shrink-0', colorClass].join(' ')}>
          <Icon size={18} className="text-white" />
        </div>

        {/* Trend */}
        {TrendIcon && trend != null && (
          <div className={['flex items-center gap-0.5 text-xs font-medium', trendColor].join(' ')}>
            <TrendIcon size={14} />
            <span>{Math.abs(trend)}%</span>
          </div>
        )}
      </div>

      <div className="mt-4">
        <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
          {title}
        </p>
        <p className="mt-1 text-2xl font-bold text-zinc-900 dark:text-zinc-50 tracking-tight">
          {value}
        </p>
      </div>
    </div>
  )
}

// ── Custom Tooltip ────────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-xl shadow-xl px-4 py-3 text-sm">
      <p className="font-semibold text-zinc-700 dark:text-zinc-300 mb-1">{label}</p>
      <p className="text-indigo-600 dark:text-indigo-400 font-bold">
        {formatCurrency(payload[0].value)}
      </p>
    </div>
  )
}

// ── Dashboard Page ────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { data: summary,       isLoading: l1 } = useQuery({ queryKey: ['billing-summary'],   queryFn: billingApi.summary })
  const { data: clients,       isLoading: l2 } = useQuery({ queryKey: ['clients'],           queryFn: () => clientsApi.list() })
  const { data: monthlyRevenue = [], isLoading: l3 } = useQuery({ queryKey: ['monthly-revenue'], queryFn: billingApi.monthlyRevenue })
  const { data: recentInvoices = [], isLoading: l4 } = useQuery({ queryKey: ['recent-invoices'], queryFn: billingApi.recent })

  const loading = l1 || l2 || l3 || l4

  return (
    <div className="p-5 md:p-8 space-y-7 max-w-7xl mx-auto">

      {/* ── Page header ── */}
      <div className="animate-fade-down">
        <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 tracking-tight">
          Bienvenido de nuevo 👋
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Aquí tienes el resumen de tu negocio hoy.
        </p>
      </div>

      {/* ── Stat cards ── */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard
            title="Clientes activos"
            value={clients?.count ?? 0}
            icon={Users}
            colorClass="bg-indigo-500"
            glowClass="card-glow-indigo"
            delay="delay-75"
          />
          <StatCard
            title="Total recaudado"
            value={formatCurrency(Number(summary?.paid_total ?? 0))}
            icon={TrendingUp}
            trend={12}
            colorClass="bg-emerald-500"
            glowClass="card-glow-green"
            delay="delay-100"
          />
          <StatCard
            title="Por cobrar"
            value={formatCurrency(Number(summary?.pending_total ?? 0))}
            icon={FileText}
            colorClass="bg-amber-500"
            glowClass="card-glow-amber"
            delay="delay-150"
          />
          <StatCard
            title="Facturas vencidas"
            value={summary?.overdue_count ?? 0}
            icon={AlertTriangle}
            colorClass="bg-red-500"
            glowClass="card-glow-red"
            delay="delay-200"
          />
        </div>
      )}

      {/* ── Revenue chart ── */}
      <div className="animate-fade-up delay-200 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Ingresos mensuales
            </h2>
            <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5">
              Últimos 6 meses
            </p>
          </div>
          <Badge variant="info" dot>En tiempo real</Badge>
        </div>

        {loading ? (
          <div className="skeleton rounded-xl" style={{ height: 220 }} />
        ) : monthlyRevenue.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-zinc-400 dark:text-zinc-600">
            <BarChart2Icon />
            <p className="text-sm mt-3 font-medium">Sin datos de ventas aún</p>
            <p className="text-xs mt-1">Las ventas aparecerán aquí cuando registres facturas pagadas.</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={monthlyRevenue} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#6366f1" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0}    />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" className="dark:stroke-zinc-800" />
              <XAxis
                dataKey="mes"
                tick={{ fontSize: 12, fill: '#a1a1aa' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v) =>
                  new Intl.NumberFormat('es-CO', {
                    notation: 'compact', maximumFractionDigits: 1,
                  }).format(v)
                }
                tick={{ fontSize: 11, fill: '#a1a1aa' }}
                axisLine={false}
                tickLine={false}
                width={52}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#6366f1', strokeWidth: 1, strokeDasharray: '4 4' }} />
              <Area
                type="monotone"
                dataKey="total"
                stroke="#6366f1"
                strokeWidth={2}
                fill="url(#revenueGradient)"
                dot={{ fill: '#6366f1', strokeWidth: 0, r: 3 }}
                activeDot={{ fill: '#6366f1', stroke: '#fff', strokeWidth: 2, r: 5 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Bottom row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

        {/* Recent invoices — 3/5 */}
        <div className="lg:col-span-3 animate-fade-up delay-300 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
          <div className="px-6 py-4 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Facturas recientes</h2>
            <a
              href="/invoices"
              className="text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              Ver todas
            </a>
          </div>

          {loading ? (
            <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-6 py-4">
                  <div className="skeleton rounded-lg w-8 h-8 shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <div className="skeleton h-3 w-28" />
                    <div className="skeleton h-2.5 w-20" />
                  </div>
                  <div className="skeleton h-5 w-16 rounded-full" />
                  <div className="skeleton h-4 w-20" />
                </div>
              ))}
            </div>
          ) : recentInvoices.length === 0 ? (
            <div className="py-12 text-center text-sm text-zinc-400 dark:text-zinc-600">
              No hay facturas recientes
            </div>
          ) : (
            <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {recentInvoices.map((inv) => {
                const st = STATUS_MAP[inv.status] ?? { label: inv.status, variant: 'default' as const }
                return (
                  <div
                    key={inv.id}
                    className="flex items-center gap-4 px-6 py-3.5 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
                  >
                    {/* Invoice number icon */}
                    <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 flex items-center justify-center shrink-0">
                      <FileText size={14} className="text-indigo-600 dark:text-indigo-400" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                        {inv.number}
                      </p>
                      <p className="text-xs text-zinc-500 dark:text-zinc-500 truncate">{inv.client}</p>
                    </div>

                    <Badge variant={st.variant} dot>{st.label}</Badge>

                    <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 shrink-0 tabular-nums">
                      {formatCurrency(inv.total)}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Summary panel — 2/5 */}
        <div className="lg:col-span-2 animate-fade-up delay-300 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 space-y-5">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Resumen de cartera
          </h2>

          {loading ? (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="flex justify-between">
                  <div className="skeleton h-3 w-24" />
                  <div className="skeleton h-3 w-16" />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-0">
              {[
                {
                  label:  'Facturas emitidas',
                  value:  summary?.total_invoices ?? 0,
                  suffix: 'docs',
                  color:  'text-zinc-700 dark:text-zinc-300',
                },
                {
                  label:  'Cotizaciones',
                  value:  summary?.total_quotes ?? 0,
                  suffix: 'docs',
                  color:  'text-zinc-700 dark:text-zinc-300',
                },
                {
                  label: 'Total recaudado',
                  value: formatCurrency(Number(summary?.paid_total ?? 0)),
                  color: 'text-emerald-600 dark:text-emerald-400 font-semibold',
                },
                {
                  label: 'Pendiente de cobro',
                  value: formatCurrency(Number(summary?.pending_total ?? 0)),
                  color: 'text-amber-600 dark:text-amber-400 font-semibold',
                },
              ].map(({ label, value, color }, i) => (
                <div key={i}>
                  {i === 2 && <div className="border-t border-dashed border-zinc-200 dark:border-zinc-700 my-3" />}
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-zinc-500 dark:text-zinc-400">{label}</span>
                    <span className={['text-sm tabular-nums', color].join(' ')}>{value}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Progress bar — collected vs pending */}
          {!loading && summary && (
            <div className="pt-2 space-y-2">
              <div className="flex justify-between text-xs text-zinc-400 dark:text-zinc-500">
                <span>Tasa de cobro</span>
                <span>
                  {summary.paid_total + summary.pending_total > 0
                    ? Math.round(
                        (Number(summary.paid_total) /
                          (Number(summary.paid_total) + Number(summary.pending_total))) *
                          100
                      )
                    : 0}%
                </span>
              </div>
              <div className="h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-full transition-all duration-700"
                  style={{
                    width:
                      summary.paid_total + summary.pending_total > 0
                        ? `${Math.round(
                            (Number(summary.paid_total) /
                              (Number(summary.paid_total) + Number(summary.pending_total))) *
                              100
                          )}%`
                        : '0%',
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Inline icon helper (avoid import just for empty state)
function BarChart2Icon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /><line x1="2" y1="20" x2="22" y2="20" />
    </svg>
  )
}
