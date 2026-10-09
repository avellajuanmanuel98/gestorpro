import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Truck } from 'lucide-react'
import { suppliersApi } from '@/api/suppliers'
import SupplierForm from '@/components/suppliers/SupplierForm'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import RowActions from '@/components/ui/RowActions'
import SearchInput from '@/components/ui/SearchInput'
import Select from '@/components/ui/Select'
import { label, SUPPLIER_CATEGORIES } from '@/lib/options'
import { ACTIVE_STATUS } from '@/lib/status'
import { useDeleteDialog } from '@/lib/useDeleteDialog'
import { useCan } from '@/store/authStore'
import type { Supplier } from '@/types'
import StatusMark from '@/components/ui/StatusMark'

export default function SuppliersPage() {
  const can = useCan()
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Supplier | 'new' | null>(null)
  const [loadingId, setLoadingId] = useState<number | null>(null)

  // La lista no trae todos los campos: al editar se carga el detalle completo
  // (si no, guardar sobrescribiría con vacíos los campos que no venían).
  const openEdit = async (item: Supplier) => {
    setLoadingId(item.id)
    try { setEditing(await suppliersApi.get(item.id)) } finally { setLoadingId(null) }
  }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['suppliers', search, category, page],
    queryFn: () => suppliersApi.list({ search: search || undefined, category: category || undefined, page }),
    placeholderData: (prev) => prev,
  })
  const del = useDeleteDialog<Supplier>((s) => suppliersApi.delete(s.id), 'suppliers', (s) => `Proveedor «${s.company_name}» eliminado`)

  const columns: Column<Supplier>[] = [
    { key: 'name', header: 'Proveedor', primary: true, cell: (s) => (
      <div className="min-w-0"><p className="font-medium text-ink truncate">{s.company_name}</p>
        {s.contact_name && <p className="text-xs text-ink-muted truncate">{s.contact_name}</p>}</div>
    ) },
    { key: 'category', header: 'Categoría', cell: (s) => <span className="text-ink-muted">{label(SUPPLIER_CATEGORIES, s.category)}</span> },
    { key: 'contact', header: 'Contacto', cell: (s) => (
      <div className="text-ink-muted min-w-0"><p className="truncate">{s.email || s.phone || '—'}</p>
        {s.email && s.phone && <p className="text-xs">{s.phone}</p>}</div>
    ) },
    { key: 'city', header: 'Ciudad', hideOnMobile: true, cell: (s) => s.city || <span className="text-ink-subtle">—</span> },
    { key: 'status', header: 'Estado', cell: (s) => <StatusMark status={ACTIVE_STATUS[s.status]} /> },
  ]

  return (
    <Page>
      <PageHeader title="Proveedores" description="A quién le compras insumos y servicios"
                  actions={can('suppliers.create') && <Button icon={<Plus size={15} />} onClick={() => setEditing('new')}>Nuevo proveedor</Button>} />

      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput label="Buscar proveedores" placeholder="Nombre, contacto o documento" value={search}
                     onChange={(v) => { setSearch(v); setPage(1) }} />
        <div className="sm:w-56">
          <Select aria-label="Categoría" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1) }}>
            <option value="">Todas las categorías</option>
            {SUPPLIER_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </Select>
        </div>
      </div>

      <DataTable caption="Proveedores" columns={columns} rows={data?.results} rowKey={(s) => s.id} isLoading={isLoading}
        pagination={{ data, onPageChange: setPage, noun: 'proveedores', isFetching }}
        rowActions={(s) => <RowActions name={s.company_name}
                                       onEdit={can('suppliers.update') && loadingId !== s.id ? () => void openEdit(s) : undefined}
                                       onDelete={can('suppliers.delete') ? () => del.open(s) : undefined} />}
        empty={search || category
          ? <EmptyState icon={<Truck size={20} />} title="Sin resultados" description="Ningún proveedor coincide con los filtros." />
          : <EmptyState icon={<Truck size={20} />} title="Aún no hay proveedores"
                        description="Registra a quienes te venden harina, lácteos, empaques y demás insumos."
                        action={can('suppliers.create') ? { label: 'Agregar proveedor', onClick: () => setEditing('new'), icon: <Plus size={14} /> } : undefined} />}
      />

      <Modal title={editing === 'new' ? 'Nuevo proveedor' : 'Editar proveedor'} isOpen={editing !== null} onClose={() => setEditing(null)} size="lg">
        {editing !== null && <SupplierForm supplier={editing === 'new' ? undefined : editing} onSuccess={() => setEditing(null)} onCancel={() => setEditing(null)} />}
      </Modal>

      <ConfirmDialog isOpen={del.target !== null} title="Eliminar proveedor" confirmLabel="Eliminar"
                     description={<>Se eliminará <strong className="text-ink">{del.target?.company_name}</strong>.</>}
                     loading={del.loading} error={del.error} onConfirm={del.confirm} onClose={del.close} />
    </Page>
  )
}
