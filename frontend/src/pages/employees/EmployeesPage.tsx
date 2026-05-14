import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Plus, Mail, Phone, Briefcase, Pencil, Trash2 } from 'lucide-react'
import { employeesApi } from '@/api/employees'
import type { Employee } from '@/types'
import Modal from '@/components/ui/Modal'
import EmployeeForm from '@/components/employees/EmployeeForm'

const DEPARTMENT_LABELS: Record<Employee['department'], string> = {
  admin:      'Administración',
  sales:      'Ventas',
  operations: 'Operaciones',
  finance:    'Finanzas',
  it:         'Tecnología',
  hr:         'Recursos Humanos',
  other:      'Otro',
}

function StatusBadge({ status }: { status: Employee['status'] }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
      status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
    }`}>
      {status === 'active' ? 'Activo' : 'Inactivo'}
    </span>
  )
}

export default function EmployeesPage() {
  const queryClient = useQueryClient()
  const [search,           setSearch]           = useState('')
  const [modalOpen,        setModalOpen]        = useState(false)
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | undefined>()

  const { data, isLoading } = useQuery({
    queryKey: ['employees', search],
    queryFn:  () => employeesApi.list({ search }),
    enabled:  search.length !== 1,
  })

  const deleteMutation = useMutation({
    mutationFn: employeesApi.delete,
    onSuccess:  () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  })

  const openCreate = () => {
    setSelectedEmployee(undefined)
    setModalOpen(true)
  }

  const openEdit = (employee: Employee) => {
    setSelectedEmployee(employee)
    setModalOpen(true)
  }

  const handleDelete = (employee: Employee) => {
    if (confirm(`¿Eliminar a ${employee.full_name}? Esta acción no se puede deshacer.`)) {
      deleteMutation.mutate(employee.id)
    }
  }

  return (
    <div className="p-4 md:p-8">
      {/* Encabezado */}
      <div className="flex items-center justify-between mb-6 md:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Empleados</h1>
          <p className="text-gray-500 mt-1">{data?.count ?? 0} empleados registrados</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />
          Nuevo empleado
        </button>
      </div>

      {/* Buscador */}
      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre, email o cargo..."
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
            <div className="text-center py-12 text-gray-500">No se encontraron empleados</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Empleado</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Contacto</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Cargo / Área</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Ingreso</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Estado</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.results.map((emp) => (
                  <tr key={emp.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-semibold text-sm shrink-0">
                          {emp.first_name[0]}{emp.last_name[0]}
                        </div>
                        <p className="font-medium text-gray-900">{emp.full_name}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-sm text-gray-600">
                        <Mail size={13} />{emp.email}
                      </div>
                      {emp.phone && (
                        <div className="flex items-center gap-1 text-sm text-gray-500 mt-1">
                          <Phone size={13} />{emp.phone}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-sm text-gray-700 font-medium">
                        <Briefcase size={13} className="text-gray-400" />
                        {emp.position}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{DEPARTMENT_LABELS[emp.department]}</p>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {emp.hire_date
                        ? new Date(emp.hire_date).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' })
                        : '—'}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={emp.status} />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEdit(emp)}
                          className="p-1.5 rounded-lg hover:bg-indigo-50 text-gray-500 hover:text-indigo-600 transition-colors"
                          title="Editar"
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          onClick={() => handleDelete(emp)}
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
        title={selectedEmployee ? 'Editar empleado' : 'Nuevo empleado'}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        size="lg"
      >
        <EmployeeForm
          employee={selectedEmployee}
          onSuccess={() => setModalOpen(false)}
        />
      </Modal>
    </div>
  )
}
