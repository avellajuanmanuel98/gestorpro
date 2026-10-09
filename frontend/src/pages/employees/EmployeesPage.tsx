import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, UserCheck } from 'lucide-react'
import { employeesApi } from '@/api/employees'
import EmployeeForm from '@/components/employees/EmployeeForm'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import RowActions from '@/components/ui/RowActions'
import SearchInput from '@/components/ui/SearchInput'
import Select from '@/components/ui/Select'
import { formatDate } from '@/lib/dates'
import { DEPARTMENTS, label } from '@/lib/options'
import { ACTIVE_STATUS } from '@/lib/status'
import { useDeleteDialog } from '@/lib/useDeleteDialog'
import { useCan } from '@/store/authStore'
import type { Employee } from '@/types'
import StatusMark from '@/components/ui/StatusMark'

export default function EmployeesPage() {
  const can = useCan()
  const [search, setSearch] = useState('')
  const [department, setDepartment] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Employee | 'new' | null>(null)
  const [loadingId, setLoadingId] = useState<number | null>(null)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['employees', search, department, page],
    queryFn: () => employeesApi.list({ search: search || undefined, department: department || undefined, page }),
    placeholderData: (prev) => prev,
  })
  const del = useDeleteDialog<Employee>((e) => employeesApi.delete(e.id), 'employees', (e) => `${e.full_name} eliminado del personal`)

  // La lista no trae todos los campos: al editar se carga el detalle completo
  const openEdit = async (e: Employee) => {
    setLoadingId(e.id)
    try { setEditing(await employeesApi.get(e.id)) } finally { setLoadingId(null) }
  }

  const columns: Column<Employee>[] = [
    { key: 'name', header: 'Nombre', primary: true, cell: (e) => (
      <div className="min-w-0"><p className="font-medium text-ink truncate">{e.full_name}</p>
        <p className="text-xs text-ink-muted truncate">{e.position}</p></div>
    ) },
    { key: 'department', header: 'Área', cell: (e) => <span className="text-ink-muted">{label(DEPARTMENTS, e.department)}</span> },
    { key: 'contact', header: 'Contacto', hideOnMobile: true, cell: (e) => <span className="text-ink-muted">{e.phone || e.email || '—'}</span> },
    { key: 'hire', header: 'Ingreso', align: 'right', cell: (e) => formatDate(e.hire_date) },
    { key: 'status', header: 'Estado', cell: (e) => <StatusMark status={ACTIVE_STATUS[e.status]} /> },
  ]

  return (
    <Page>
      <PageHeader title="Personal" description="Fichas de las personas que trabajan en la empresa"
                  actions={can('hr.manage') && <Button icon={<Plus size={15} />} onClick={() => setEditing('new')}>Nuevo empleado</Button>} />

      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput label="Buscar personal" placeholder="Nombre, cargo o documento" value={search}
                     onChange={(v) => { setSearch(v); setPage(1) }} />
        <div className="sm:w-56">
          <Select aria-label="Área" value={department} onChange={(e) => { setDepartment(e.target.value); setPage(1) }}>
            <option value="">Todas las áreas</option>
            {DEPARTMENTS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
          </Select>
        </div>
      </div>

      <DataTable caption="Personal" columns={columns} rows={data?.results} rowKey={(e) => e.id} isLoading={isLoading}
        pagination={{ data, onPageChange: setPage, noun: 'empleados', isFetching }}
        rowActions={(e) => can('hr.manage') && (
          <RowActions name={e.full_name} onEdit={loadingId === e.id ? undefined : () => void openEdit(e)} onDelete={() => del.open(e)} />
        )}
        empty={search || department
          ? <EmptyState icon={<UserCheck size={20} />} title="Sin resultados" description="Nadie coincide con los filtros." />
          : <EmptyState icon={<UserCheck size={20} />} title="Aún no hay fichas de personal"
                        description="Registra a tu equipo: panaderos, cajeros, domiciliarios…"
                        action={can('hr.manage') ? { label: 'Registrar empleado', onClick: () => setEditing('new'), icon: <Plus size={14} /> } : undefined} />}
      />

      <Modal title={editing === 'new' ? 'Nuevo empleado' : 'Editar empleado'} isOpen={editing !== null} onClose={() => setEditing(null)} size="lg">
        {editing !== null && <EmployeeForm employee={editing === 'new' ? undefined : editing} onSuccess={() => setEditing(null)} onCancel={() => setEditing(null)} />}
      </Modal>

      <ConfirmDialog isOpen={del.target !== null} title="Eliminar ficha" confirmLabel="Eliminar"
                     description={<>Se eliminará la ficha de <strong className="text-ink">{del.target?.full_name}</strong>. Si solo dejó
                       de trabajar contigo, mejor márcala como inactiva para conservar el historial.</>}
                     loading={del.loading} error={del.error} onConfirm={del.confirm} onClose={del.close} />
    </Page>
  )
}
