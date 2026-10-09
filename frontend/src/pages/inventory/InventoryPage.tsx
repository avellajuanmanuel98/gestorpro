import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Boxes, Plus, Tags } from 'lucide-react'
import { inventoryApi } from '@/api/inventory'
import CategoryForm from '@/components/inventory/CategoryForm'
import ProductForm from '@/components/inventory/ProductForm'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import RowActions from '@/components/ui/RowActions'
import SearchInput from '@/components/ui/SearchInput'
import Select from '@/components/ui/Select'
import Tabs from '@/components/ui/Tabs'
import { formatCOP } from '@/lib/money'
import { useDeleteDialog } from '@/lib/useDeleteDialog'
import { useCan } from '@/store/authStore'
import type { Category, Product } from '@/types'
import StatusMark from '@/components/ui/StatusMark'
import { ACTIVE_STATUS } from '@/lib/status'

function ProductsTab({ canManage }: { canManage: boolean }) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Product | 'new' | null>(null)
  const [loadingId, setLoadingId] = useState<number | null>(null)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['products', search, filter, page],
    queryFn: () => inventoryApi.listProducts({
      search: search || undefined, page,
      ...(filter === 'low' ? { low_stock: 'true' } : filter === 'inactive' ? { is_active: false } : filter === 'active' ? { is_active: true } : {}),
    }),
    placeholderData: (prev) => prev,
  })
  const del = useDeleteDialog<Product>((p) => inventoryApi.deleteProduct(p.id), 'products', (p) => `«${p.name}» eliminado`)

  // La lista no trae la descripción: al editar se carga el detalle completo
  const openEdit = async (p: Product) => {
    setLoadingId(p.id)
    try { setEditing(await inventoryApi.getProduct(p.id)) } finally { setLoadingId(null) }
  }

  const columns: Column<Product>[] = [
    { key: 'name', header: 'Producto', primary: true, cell: (p) => (
      <div className="min-w-0"><p className="font-medium text-ink truncate">{p.name}</p><p className="text-xs text-ink-muted">{p.code}</p></div>
    ) },
    { key: 'category', header: 'Categoría', cell: (p) => p.category_name ?? <span className="text-ink-subtle">—</span> },
    { key: 'price', header: 'Precio', align: 'right', cell: (p) => formatCOP(p.price) },
    { key: 'tax', header: 'IVA', align: 'right', hideOnMobile: true, cell: (p) => `${Number(p.tax_rate)} %` },
    { key: 'stock', header: 'Stock', align: 'right', cell: (p) => p.product_type === 'service'
      ? <span className="text-ink-subtle">Servicio</span>
      : <span className={p.is_low_stock ? 'text-warning font-medium inline-flex items-center gap-1' : ''}>
          {p.is_low_stock && <AlertTriangle size={13} aria-label="Stock bajo" />}{p.stock.toLocaleString('es-CO')}
        </span> },
    { key: 'status', header: 'Estado', cell: (p) => <StatusMark status={ACTIVE_STATUS[p.is_active ? 'active' : 'inactive']} /> },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <SearchInput label="Buscar productos" placeholder="Nombre o código" value={search} onChange={(v) => { setSearch(v); setPage(1) }} />
        <div className="sm:w-48">
          <Select aria-label="Filtro" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1) }}>
            <option value="">Todos</option>
            <option value="active">Activos</option>
            <option value="low">Con stock bajo</option>
            <option value="inactive">Inactivos</option>
          </Select>
        </div>
        <div className="sm:ml-auto">
          {canManage && <Button icon={<Plus size={15} />} onClick={() => setEditing('new')}>Nuevo producto</Button>}
        </div>
      </div>

      <DataTable caption="Productos" columns={columns} rows={data?.results} rowKey={(p) => p.id} isLoading={isLoading}
        pagination={{ data, onPageChange: setPage, noun: 'productos', isFetching }}
        rowActions={(p) => canManage && (
          <RowActions name={p.name} onEdit={loadingId === p.id ? undefined : () => void openEdit(p)} onDelete={() => del.open(p)} />
        )}
        empty={search || filter
          ? <EmptyState icon={<Boxes size={20} />} title="Sin resultados" description="Ningún producto coincide con los filtros." />
          : <EmptyState icon={<Boxes size={20} />} title="Tu catálogo está vacío"
                        description="Agrega lo que vendes: panes, bebidas, tortas por porción…"
                        action={canManage ? { label: 'Agregar producto', onClick: () => setEditing('new'), icon: <Plus size={14} /> } : undefined} />}
      />

      <Modal title={editing === 'new' ? 'Nuevo producto' : 'Editar producto'} isOpen={editing !== null} onClose={() => setEditing(null)} size="lg">
        {editing !== null && <ProductForm product={editing === 'new' ? undefined : editing} onSuccess={() => setEditing(null)} onCancel={() => setEditing(null)} />}
      </Modal>
      <ConfirmDialog isOpen={del.target !== null} title="Eliminar producto" confirmLabel="Eliminar"
                     description={<>Se eliminará <strong className="text-ink">{del.target?.name}</strong>. Si aparece en facturas no podrá
                       eliminarse; en ese caso desactívalo.</>}
                     loading={del.loading} error={del.error} onConfirm={del.confirm} onClose={del.close} />
    </div>
  )
}

function CategoriesTab({ canManage }: { canManage: boolean }) {
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Category | 'new' | null>(null)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['categories', page], queryFn: () => inventoryApi.listCategories({ page }), placeholderData: (prev) => prev,
  })
  const del = useDeleteDialog<Category>((c) => inventoryApi.deleteCategory(c.id), 'categories', (c) => `Categoría «${c.name}» eliminada`)

  const columns: Column<Category>[] = [
    { key: 'name', header: 'Categoría', primary: true, cell: (c) => <span className="font-medium">{c.name}</span> },
    { key: 'description', header: 'Descripción', cell: (c) => <span className="text-ink-muted">{c.description || '—'}</span> },
    { key: 'count', header: 'Productos', align: 'right', cell: (c) => c.products_count },
  ]

  return (
    <div className="space-y-4">
      {canManage && <div className="flex justify-end"><Button icon={<Plus size={15} />} onClick={() => setEditing('new')}>Nueva categoría</Button></div>}
      <DataTable caption="Categorías" columns={columns} rows={data?.results} rowKey={(c) => c.id} isLoading={isLoading}
        pagination={{ data, onPageChange: setPage, noun: 'categorías', isFetching }}
        rowActions={(c) => canManage && <RowActions name={c.name} onEdit={() => setEditing(c)} onDelete={() => del.open(c)} />}
        empty={<EmptyState icon={<Tags size={20} />} title="Sin categorías" description="Las categorías ordenan tu catálogo y tus reportes."
                           action={canManage ? { label: 'Crear categoría', onClick: () => setEditing('new') } : undefined} />}
      />
      <Modal title={editing === 'new' ? 'Nueva categoría' : 'Editar categoría'} isOpen={editing !== null} onClose={() => setEditing(null)} size="sm">
        {editing !== null && <CategoryForm category={editing === 'new' ? undefined : editing} onSuccess={() => setEditing(null)} onCancel={() => setEditing(null)} />}
      </Modal>
      <ConfirmDialog isOpen={del.target !== null} title="Eliminar categoría" confirmLabel="Eliminar"
                     description={<>Se eliminará <strong className="text-ink">{del.target?.name}</strong>. Sus productos quedarán sin categoría.</>}
                     loading={del.loading} error={del.error} onConfirm={del.confirm} onClose={del.close} />
    </div>
  )
}

export default function InventoryPage() {
  const canManage = useCan()('catalog.manage')
  const [tab, setTab] = useState<'products' | 'categories'>('products')
  return (
    <Page>
      <PageHeader title="Productos" description="Tu catálogo de venta, precios y alertas de stock" />
      <Tabs label="Secciones del catálogo" value={tab} onChange={setTab}
            tabs={[{ id: 'products', label: 'Productos' }, { id: 'categories', label: 'Categorías' }]} />
      {tab === 'products' ? <ProductsTab canManage={canManage} /> : <CategoriesTab canManage={canManage} />}
    </Page>
  )
}
