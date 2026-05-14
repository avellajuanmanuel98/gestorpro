import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Plus, Mail, Phone, Globe, Pencil, Trash2 } from 'lucide-react'
import { suppliersApi } from '@/api/suppliers'
import type { Supplier } from '@/types'
import Modal from '@/components/ui/Modal'
import SupplierForm from '@/components/suppliers/SupplierForm'

const CATEGORY_LABELS: Record<Supplier['category'], string> = {
  materials:  'Materiales e insumos',
  services:   'Servicios',
  technology: 'Tecnología',
  logistics:  'Logística y transporte',
  marketing:  'Marketing y publicidad',
  other:      'Otro',
}

const CATEGORY_COLORS: Record<Supplier['category'], string> = {
  materials:  'bg-orange-100 text-orange-700',
  services:   'bg-blue-100 text-blue-700',
  technology: 'bg-purple-100 text-purple-700',
  logistics:  'bg-yellow-100 text-yellow-700',
  marketing:  'bg-pink-100 text-pink-700',
  other:      'bg-gray-100 text-gray-600',
}

function StatusBadge({ status }: { status: Supplier['status'] }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
      status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
    }`}>
      {status === 'active' ? 'Activo' : 'Inactivo'}
    </span>
  )
}

function CategoryBadge({ category }: { category: Supplier['category'] }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[category]}`}>
      {CATEGORY_LABELS[category]}
    </span>
  )
}

export default function SuppliersPage() {
  const queryClient = useQueryClient()
  const [search,           setSearch]           = useState('')
  const [modalOpen,        setModalOpen]        = useState(false)
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | undefined>()

  const { data, isLoading } = useQuery({
    queryKey: ['suppliers', search],
    queryFn:  () => suppliersApi.list({ search }),
    enabled:  search.length !== 1,
  })

  const deleteMutation = useMutation({
    mutationFn: suppliersApi.delete,
    onSuccess:  () => queryClient.invalidateQueries({ queryKey: ['suppliers'] }),
  })

  const openCreate = () => {
    setSelectedSupplier(undefined)
    setModalOpen(true)
  }

  const openEdit = (supplier: Supplier) => {
    setSelectedSupplier(supplier)
    setModalOpen(true)
  }

  const handleDelete = (supplier: Supplier) => {
    if (confirm(`¿Eliminar a ${supplier.company_name}? Esta acción no se puede deshacer.`)) {
      deleteMutation.mutate(supplier.id)
    }
  }

  return (
    <div className="p-4 md:p-8">
      {/* Encabezado */}
      <div className="flex items-center justify-between mb-6 md:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Proveedores</h1>
          <p className="text-gray-500 mt-1">{data?.count ?? 0} proveedores registrados</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />
          Nuevo proveedor
        </button>
      </div>

      {/* Buscador */}
      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre, contacto o email..."
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
            <div className="text-center py-12 text-gray-500">No se encontraron proveedores</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Proveedor</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Contacto</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Categoría</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Estado</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.results.map((supplier) => (
                  <tr key={supplier.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-900">{supplier.company_name}</p>
                      {supplier.contact_name && (
                        <p className="text-sm text-gray-500">{supplier.contact_name}</p>
                      )}
                      {supplier.city && (
                        <p className="text-xs text-gray-400">{supplier.city}</p>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {supplier.email && (
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <Mail size={13} />{supplier.email}
                        </div>
                      )}
                      {supplier.phone && (
                        <div className="flex items-center gap-1 text-sm text-gray-500 mt-1">
                          <Phone size={13} />{supplier.phone}
                        </div>
                      )}
                      {supplier.website && (
                        <a
                          href={supplier.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-sm text-indigo-500 hover:text-indigo-700 mt-1"
                        >
                          <Globe size={13} />Sitio web
                        </a>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <CategoryBadge category={supplier.category} />
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={supplier.status} />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEdit(supplier)}
                          className="p-1.5 rounded-lg hover:bg-indigo-50 text-gray-500 hover:text-indigo-600 transition-colors"
                          title="Editar"
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          onClick={() => handleDelete(supplier)}
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

      <Modal
        title={selectedSupplier ? 'Editar proveedor' : 'Nuevo proveedor'}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        size="lg"
      >
        <SupplierForm
          supplier={selectedSupplier}
          onSuccess={() => setModalOpen(false)}
        />
      </Modal>
    </div>
  )
}
