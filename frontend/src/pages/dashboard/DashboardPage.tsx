import { useQuery } from '@tanstack/react-query'
import { Users, FileText, TrendingUp, AlertTriangle } from 'lucide-react'
import { billingApi } from '@/api/billing'
import { clientsApi } from '@/api/clients'

// Tarjeta de estadística reutilizable
function StatCard({
  title, value, icon: Icon, color
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

function formatCurrency(value: string | number) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
  }).format(Number(value))
}

export default function DashboardPage() {
  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['billing-summary'],
    queryFn: billingApi.summary,
  })

  const { data: clients, isLoading: loadingClients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  })

  if (loadingSummary || loadingClients) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    )
  }

  return (
    <div className="p-4 md:p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Resumen general del negocio</p>
      </div>

      {/* Tarjetas de estadísticas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Clientes activos"
          value={clients?.count ?? 0}
          icon={Users}
          color="bg-indigo-500"
        />
        <StatCard
          title="Total facturado (pagado)"
          value={formatCurrency(summary?.paid_total ?? 0)}
          icon={TrendingUp}
          color="bg-green-500"
        />
        <StatCard
          title="Por cobrar"
          value={formatCurrency(summary?.pending_total ?? 0)}
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

      {/* Resumen de documentos */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Documentos emitidos</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Facturas</span>
              <span className="font-semibold text-gray-900">{summary?.total_invoices ?? 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Cotizaciones</span>
              <span className="font-semibold text-gray-900">{summary?.total_quotes ?? 0}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Estado de cartera</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Recaudado</span>
              <span className="font-semibold text-green-600">{formatCurrency(summary?.paid_total ?? 0)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Pendiente</span>
              <span className="font-semibold text-yellow-600">{formatCurrency(summary?.pending_total ?? 0)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
