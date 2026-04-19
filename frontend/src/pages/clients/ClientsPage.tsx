import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Plus, Mail, Phone, MapPin, Pencil, Trash2 } from 'lucide-react'
import { clientsApi } from '@/api/clients'
import type { Client } from '@/types'
import Modal from '@/components/ui/Modal'
import ClientForm from '@/components/clients/ClientForm'

function StatusBadge({ status }: { status: Client['status'] }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
      status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
    }`}>
      {status === 'active' ? 'Activo' : 'Inactivo'}
    </span>
  )
}

export default function ClientsPage() {
  const queryClient = useQueryClient()
  const [search,        setSearch]        = useState('')
  const [modalOpen,     setModalOpen]     = useState(false)
  const [selectedClient, setSelectedClient] = useState<Client | undefined>()

  const { data, isLoading } = useQuery({
    queryKey: ['clients', search],
    queryFn:  () => clientsApi.list({ search }),
    enabled:  search.length !== 1,
  })

  const deleteMutation = useMutation({
    mutationFn: clientsApi.delete,
    onSuccess:  () => queryClient.invalidateQueries({ queryKey: ['clients'] }),
  })

  const openCreate = () => {
    setSelectedClient(undefined)
    setModalOpen(true)
  }

  const openEdit = (client: Client) => {
    setSelectedClient(client)
    setModalOpen(true)
  }

  const handleDelete = (client: Client) => {
    if (confirm(`¿Eliminar a ${client.full_name}? Esta acción no se puede deshacer.`)) {
      deleteMutation.mutate(client.id)
    }
  }

  return (
    <div className="p-4 md:p-8">
      {/* Encabezado */}
      <div className="flex items-center justify-between mb-6 md:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-gray-500 mt-1">{data?.count ?? 0} clientes registrados</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />
          Nuevo cliente
        </button>
      </div>

      {/* Buscador */}
      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre, email o documento..."
          className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Tabla */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
          {data?.results.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No se encontraron clientes</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Cliente</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Contacto</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Ciudad</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Estado</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.results.map((client) => (
                  <tr key={client.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-900">{client.full_name}</p>
                      {client.company_name && (
                        <p className="text-sm text-gray-500">{client.company_name}</p>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-sm text-gray-600">
                        <Mail size={13} />{client.email}
                      </div>
                      {client.phone && (
                        <div className="flex items-center gap-1 text-sm text-gray-500 mt-1">
                          <Phone size={13} />{client.phone}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {client.city && (
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <MapPin size={13} />{client.city}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={client.status} />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEdit(client)}
                          className="p-1.5 rounded-lg hover:bg-indigo-50 text-gray-500 hover:text-indigo-600 transition-colors"
                          title="Editar"
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          onClick={() => handleDelete(client)}
                          className="p-1.5 rounded-lg hover:bg-red-50 text-gray-500 hover:text-red-600 transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Modal de creación/edición */}
      <Modal
        title={selectedClient ? 'Editar cliente' : 'Nuevo cliente'}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        size="lg"
      >
        <ClientForm
          client={selectedClient}
          onSuccess={() => setModalOpen(false)}
        />
      </Modal>
    </div>
  )
}
