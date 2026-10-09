import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Users } from 'lucide-react'
import { customersApi } from '@/api/customers'
import ClientForm from '@/components/clients/ClientForm'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import SearchInput from '@/components/ui/SearchInput'
import RowActions from '@/components/ui/RowActions'
import Select from '@/components/ui/Select'
import { ACTIVE_STATUS } from '@/lib/status'
import { useDeleteDialog } from '@/lib/useDeleteDialog'
import { useCan } from '@/store/authStore'
import type { Customer } from '@/types'

export default function ClientsPage() {
  const can = useCan()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Customer | 'new' | null>(null)
  const [loadingId, setLoadingId] = useState<number | null>(null)

  // La lista no trae todos los campos: al editar se carga el detalle completo
  // (si no, guardar sobrescribiría con vacíos los campos que no venían).
  const openEdit = async (item: Customer) => {
    setLoadingId(item.id)
    try { setEditing(await customersApi.get(item.id)) } finally { setLoadingId(null) }
  }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['customers', search, status, page],
    queryFn: () => customersApi.list({ search: search || undefined, status: status || undefined, page }),
    placeholderData: (prev) => prev,
  })
  const del = useDeleteDialog<Customer>((c) => customersApi.delete(c.id), 'customers', (c) => `Cliente «${c.full_name}» eliminado`)
  const filtered = Boolean(search || status)

  const columns: Column<Customer>[] = [
    { key: 'name', header: 'Cliente', primary: true, cell: (c) => (
      <div className="min-w-0">
        <p className="font-medium text-ink truncate">{c.company_name || c.full_name}</p>
        {c.company_name && <p className="text-xs text-ink-muted truncate">{c.full_name}</p>}
      </div>
    ) },
    { key: 'doc', header: 'Documento', cell: (c) => c.document_number || <span className="text-ink-subtle">—</span> },
    { key: 'contact', header: 'Contacto', cell: (c) => (
      <div className="text-ink-muted min-w-0"><p className="truncate">{c.email || c.phone || '—'}</p>
        {c.email && c.phone && <p className="text-xs">{c.phone}</p>}</div>
    ) },
    { key: 'city', header: 'Ciudad', hideOnMobile: true, cell: (c) => c.city || <span className="text-ink-subtle">—</span> },
    { key: 'status', header: 'Estado', cell: (c) => <Badge variant={ACTIVE_STATUS[c.status].variant}>{ACTIVE_STATUS[c.status].label}</Badge> },
  ]

  return (
    <Page>
      <PageHeader title="Clientes" description="Personas y empresas a las que les vendes"
                  actions={can('customers.create') && (
                    <Button icon={<Plus size={15} />} onClick={() => setEditing('new')}>Nuevo cliente</Button>
                  )} />

      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput label="Buscar clientes" placeholder="Nombre, documento o email" value={search}
                     onChange={(v) => { setSearch(v); setPage(1) }} />
        <div className="sm:w-44">
          <Select aria-label="Estado" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
            <option value="">Todos los estados</option>
            <option value="active">Activos</option>
            <option value="inactive">Inactivos</option>
          </Select>
        </div>
      </div>

      <DataTable
        caption="Clientes" columns={columns} rows={data?.results} rowKey={(c) => c.id} isLoading={isLoading}
        pagination={{ data, onPageChange: setPage, noun: 'clientes', isFetching }}
        rowActions={(c) => (
          <RowActions name={c.full_name}
                      onEdit={can('customers.update') && loadingId !== c.id ? () => void openEdit(c) : undefined}
                      onDelete={can('customers.delete') ? () => del.open(c) : undefined} />
        )}
        empty={filtered
          ? <EmptyState icon={<Users size={20} />} title="Sin resultados" description="Ningún cliente coincide con la búsqueda." />
          : <EmptyState icon={<Users size={20} />} title="Aún no hay clientes"
                        description="Registra a tus clientes frecuentes y empresas para facturarles."
                        action={can('customers.create') ? { label: 'Agregar cliente', onClick: () => setEditing('new'), icon: <Plus size={14} /> } : undefined} />}
      />

      <Modal title={editing === 'new' ? 'Nuevo cliente' : 'Editar cliente'} isOpen={editing !== null}
             onClose={() => setEditing(null)} size="lg">
        {editing !== null && (
          <ClientForm client={editing === 'new' ? undefined : editing} onSuccess={() => setEditing(null)} onCancel={() => setEditing(null)} />
        )}
      </Modal>

      <ConfirmDialog isOpen={del.target !== null} title="Eliminar cliente" confirmLabel="Eliminar"
                     description={<>Se eliminará <strong className="text-ink">{del.target?.full_name}</strong>. Si tiene documentos
                       asociados no podrá eliminarse; en ese caso márcalo como inactivo.</>}
                     loading={del.loading} error={del.error} onConfirm={del.confirm} onClose={del.close} />
    </Page>
  )
}
