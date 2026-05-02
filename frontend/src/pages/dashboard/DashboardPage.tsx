import { useQuery } from '@tanstack/react-query'
import { Users, FileText, TrendingUp, AlertTriangle } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { billingApi } from '@/api/billing'
import { clientsApi } from '@/api/clients'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCurrency(value: number) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
  }).format(value)
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft:     { label: 'Borrador',  color: 'bg-gray-100 text-gray-600' },
  sent:      { label: 'Enviada',   color: 'bg-blue-100 text-blue-700' },
  paid:      { label: 'Pagada',    color: 'bg-green-100 text-green-700' },
  overdue:   { label: 'Vencida',   color: 'bg-red-100 text-red-700' },
  cancelled: { label: 'Cancelada', color: 'bg-gray-100 text-gray-500' },
}

// ── Sub-componentes ───────────────────────────────────────────────────────────

function StatCard({
  title, value, icon: Icon, color,
}: {
  title: string
  value: string | number
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  )
}

// Tooltip personalizado para la gráfica
function CustomTooltip({ active, payload, label }: any) {
  if (active && payload?.length) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-4 py-2">
        <p className="text-sm font-semibold text-gray-700">{label}</p>
        <p className="text-sm text-indigo-600">{formatCurrency(payload[0].value)}</p>
      </div>
    )
  }
  return null
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['billing-summary'],
    queryFn: billingApi.summary,
  })

  const { data: clients, isLoading: loadingClients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  })

  const { data: monthlyRevenue = [], isLoading: loadingRevenue } = useQuery({
    queryKey: ['monthly-revenue'],
    queryFn: billingApi.monthlyRevenue,
  })

  const { data: recentInvoices = [], isLoading: loadingRecent } = useQuery({
    queryKey: ['recent-invoices'],
    queryFn: billingApi.recent,
  })

  const loading = loadingSummary || loadingClients || loadingRevenue || loadingRecent

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    )
  }

  return (
    <div className="p-4 md:p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Resumen general del negocio</p>
      </div>

      {/* Tarjetas de métricas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Clientes activos"
          value={clients?.count ?? 0}
          icon={Users}
          color="bg-indigo-500"
        />
        <StatCard
          title="Total recaudado"
          value={formatCurrency(Number(summary?.paid_total ?? 0))}
          icon={TrendingUp}
          color="bg-green-500"
        />
        <StatCard
          title="Por cobrar"
          value={formatCurrency(Number(summary?.pending_total ?? 0))}
          icon={FileText}
          color="bg-yellow-500"
        />
        <StatCard
          title="Facturas vencidas"
          value={summary?.overdue_count ?? 0}
          icon={AlertTriangle}
          color="bg-red-500"
        />
      </div>

      {/* Gráfica de ventas mensuales */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-6">Ventas mensuales (últimos 6 meses)</h3>
        {monthlyRevenue.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">Sin datos de ventas aún</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={monthlyRevenue} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="mes" tick={{ fontSize: 13 }} />
              <YAxis
                tickFormatter={(v) =>
                  new Intl.NumberFormat('es-CO', {
                    notation: 'compact', maximumFractionDigits: 1,
                  }).format(v)
                }
                tick={{ fontSize: 12 }}
                width={60}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="total" fill="#6366f1" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Facturas recientes + Estado de cartera */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Facturas recientes */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Facturas recientes</h3>
          {recentInvoices.length === 0 ? (
            <p className="text-sm text-gray-400">Sin facturas aún</p>
          ) : (
            <div className="space-y-3">
              {recentInvoices.map((inv) => {
                const st = STATUS_LABELS[inv.status] ?? { label: inv.status, color: 'bg-gray-100 text-gray-500' }
                return (
                  <div key={inv.id} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{inv.number}</p>
                      <p className="text-xs text-gray-500">{inv.client}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${st.color}`}>
                        {st.label}
                      </span>
                      <span className="text-sm font-semibold text-gray-900">
                        {formatCurrency(inv.total)}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Estado de cartera */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Documentos emitidos</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Facturas</span>
              <span className="font-semibold text-gray-900">{summary?.total_invoices ?? 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Cotizaciones</span>
              <span className="font-semibold text-gray-900">{summary?.total_quotes ?? 0}</span>
            </div>
            <hr className="border-gray-100" />
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Recaudado</span>
              <span className="font-semibold text-green-600">
                {formatCurrency(Number(summary?.paid_total ?? 0))}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Pendiente</span>
              <span className="font-semibold text-yellow-600">
                {formatCurrency(Number(summary?.pending_total ?? 0))}
              </span>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
