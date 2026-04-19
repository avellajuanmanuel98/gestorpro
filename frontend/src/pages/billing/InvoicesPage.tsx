import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Search } from 'lucide-react'
import { billingApi } from '@/api/billing'
import type { Invoice } from '@/types'
import Modal from '@/components/ui/Modal'
import InvoiceForm from '@/components/billing/InvoiceForm'

const STATUS_LABELS: Record<Invoice['status'], { label: string; color: string }> = {
  draft:     { label: 'Borrador',  color: 'bg-gray-100 text-gray-600'     },
  sent:      { label: 'Enviada',   color: 'bg-blue-100 text-blue-700'     },
  paid:      { label: 'Pagada',    color: 'bg-green-100 text-green-700'   },
  overdue:   { label: 'Vencida',   color: 'bg-red-100 text-red-700'       },
  cancelled: { label: 'Cancelada', color: 'bg-orange-100 text-orange-700' },
}

function formatCurrency(value: string) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', minimumFractionDigits: 0,
  }).format(Number(value))
}

export default function InvoicesPage() {
  const [search,       setSearch]       = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [modalOpen,    setModalOpen]    = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['invoices', search, statusFilter],
    queryFn:  () => billingApi.list({ status: statusFilter || undefined }),
  })

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-center justify-between mb-6 md:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Facturas</h1>
          <p className="text-gray-500 mt-1">{data?.count ?? 0} documentos</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />
          Nueva factura
        </button>
      </div>

      {/* Filtros */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por número o cliente..."
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">Todos los estados</option>
          <option value="draft">Borrador</option>
          <option value="sent">Enviada</option>
          <option value="paid">Pagada</option>
          <option value="overdue">Vencida</option>
          <option value="cancelled">Cancelada</option>
        </select>
      </div>

      {/* Tabla */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
          {data?.results.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No hay facturas</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Número</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Cliente</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Fecha</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Vence</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Total</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.results.map((invoice) => {
                  const status = STATUS_LABELS[invoice.status]
                  return (
                    <tr key={invoice.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 font-medium text-indigo-600">{invoice.number}</td>
                      <td className="px-6 py-4 text-sm text-gray-900">{invoice.client_name}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{invoice.issue_date}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{invoice.due_date}</td>
                      <td className="px-6 py-4 text-sm font-semibold text-gray-900">
                        {formatCurrency(invoice.total)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${status.color}`}>
                          {status.label}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Modal nueva factura */}
      <Modal
        title="Nueva factura"
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        size="lg"
      >
        <InvoiceForm onSuccess={() => setModalOpen(false)} />
      </Modal>
    </div>
  )
}
