import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Boxes, PackagePlus, Plus, Tags, Wheat } from 'lucide-react'
import { catalogApi, type ItemGroup } from '@/api/catalog'
import CategoryForm from '@/components/inventory/CategoryForm'
import ItemForm from '@/components/inventory/ItemForm'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import RowActions from '@/components/ui/RowActions'
import SearchInput from '@/components/ui/SearchInput'
import Select from '@/components/ui/Select'
import StatusMark from '@/components/ui/StatusMark'
import Tabs from '@/components/ui/Tabs'
import { formatQty, formatUnitCost, ITEM_KIND_LABEL } from '@/lib/catalog'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { ACTIVE_STATUS } from '@/lib/status'
import { useDeleteDialog } from '@/lib/useDeleteDialog'
import { useAuthStore, useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'
import type { Category, Item } from '@/types'

const COPY = {
  products: {
    title: 'Productos', description: 'Lo que vendes: precios, márgenes y existencias',
    noun: 'producto', plural: 'productos', newLabel: 'Nuevo producto', searchLabel: 'Buscar productos',
    emptyTitle: 'Tu catálogo está vacío', emptyText: 'Agrega lo que vendes: panes, bebidas, tortas por porción…',
    categoryKind: 'product' as const, icon: Boxes,
  },
  ingredients: {
    title: 'Ingredientes', description: 'Materias primas y empaques: unidades, costo y existencias',
    noun: 'ingrediente', plural: 'ingredientes', newLabel: 'Nuevo ingrediente', searchLabel: 'Buscar ingredientes',
    emptyTitle: 'Aún no tienes ingredientes', emptyText: 'Registra harina, huevos, mantequilla, empaques… con su unidad y su costo.',
    categoryKind: 'ingredient' as const, icon: Wheat,
  },
}

/** Las panaderías hablan de "ingredientes"; el resto de negocios, de "insumos". */
function useCopy(group: ItemGroup) {
  const isBakery = useAuthStore((s) => s.session?.tenant?.vertical) === 'bakery'
  if (group === 'products' || isBakery) return COPY[group]
  return { ...COPY.ingredients, title: 'Insumos', description: 'Materias primas, insumos y empaques: unidades, costo y existencias',
           noun: 'insumo', plural: 'insumos', newLabel: 'Nuevo insumo', searchLabel: 'Buscar insumos',
           emptyTitle: 'Aún no tienes insumos', emptyText: 'Registra las materias primas e insumos con su unidad y su costo.' }
}

function Stock({ item }: { item: Item }) {
  if (item.kind === 'service') return <span className="text-ink-subtle">—</span>
  return (
    <span className={item.is_low_stock ? 'text-warning font-medium inline-flex items-center gap-1' : 'num'}>
      {item.is_low_stock && <AlertTriangle size={13} aria-label="Bajo el mínimo" />}
      {formatQty(item.stock, item.unit_symbol)}
    </span>
  )
}

function ItemsTab({ group, canManage }: { group: ItemGroup; canManage: boolean }) {
  const copy = useCopy(group)
  const can = useCan()
  const canSeeCosts = can('catalog.view_costs')
  const isBakery = useAuthStore((s) => s.session?.tenant?.vertical) === 'bakery'
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Item | 'new' | null>(null)
  const [loadingId, setLoadingId] = useState<number | null>(null)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['items', group, search, filter, page],
    queryFn: () => catalogApi.listItems({
      group, search: search || undefined, page,
      ...(filter === 'low' ? { low_stock: 'true' } : filter === 'inactive' ? { is_active: false }
        : filter === 'active' ? { is_active: true } : filter ? { kind: filter as Item['kind'] } : {}),
    }),
    placeholderData: (prev) => prev,
  })
  const del = useDeleteDialog<Item>((i) => catalogApi.deleteItem(i.id), 'items', (i) => `«${i.name}» eliminado`)
  const starter = useMutation({
    mutationFn: catalogApi.loadStarterCatalog,
    onSuccess: ({ created }) => {
      queryClient.invalidateQueries({ queryKey: ['items'] })
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      toast.success(`${created} ingredientes agregados. Completa su costo y existencia.`)
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })

  // La lista no trae todos los campos: al editar se carga el detalle completo
  const openEdit = async (i: Item) => {
    setLoadingId(i.id)
    try { setEditing(await catalogApi.getItem(i.id)) } finally { setLoadingId(null) }
  }

  const nameCell: Column<Item> = {
    key: 'name', header: copy.noun[0].toUpperCase() + copy.noun.slice(1), primary: true, cell: (i) => (
      <div className="min-w-0">
        <p className="font-medium text-ink truncate">{i.name}</p>
        <p className="text-xs text-ink-muted">{i.code}{group === 'products' && i.kind !== 'finished_good' && ` · ${ITEM_KIND_LABEL[i.kind]}`}
          {group === 'ingredients' && i.is_sellable && ' · También se vende'}</p>
      </div>
    ),
  }
  const category: Column<Item> = {
    key: 'category', header: 'Categoría', hideOnMobile: true,
    cell: (i) => i.category_name ?? <span className="text-ink-subtle">—</span>,
  }
  const status: Column<Item> = {
    key: 'status', header: 'Estado', cell: (i) => <StatusMark status={ACTIVE_STATUS[i.is_active ? 'active' : 'inactive']} />,
  }
  const costCols: Column<Item>[] = !canSeeCosts ? [] : group === 'products' ? [
    { key: 'cost', header: 'Costo', align: 'right', hideOnMobile: true,
      cell: (i) => (Number(i.avg_cost) > 0 ? formatUnitCost(i.avg_cost) : <span className="text-ink-subtle">—</span>) },
    { key: 'margin', header: 'Margen', align: 'right',
      cell: (i) => (i.margin_pct ? `${Number(i.margin_pct).toLocaleString('es-CO')} %` : <span className="text-ink-subtle">—</span>) },
  ] : [
    { key: 'cost', header: 'Costo / unidad', align: 'right',
      cell: (i) => (Number(i.avg_cost) > 0
        ? <span className="num">{formatUnitCost(i.avg_cost)}<span className="text-ink-subtle"> / {i.unit_symbol}</span></span>
        : <span className="text-ink-subtle">Sin costo</span>) },
    { key: 'value', header: 'Valor', align: 'right', hideOnMobile: true, cell: (i) => formatCOP(i.stock_value) },
  ]
  const columns: Column<Item>[] = group === 'products'
    ? [nameCell, category,
       { key: 'price', header: 'Precio', align: 'right', cell: (i) => (
         <span className="num">{formatCOP(i.price)}{i.unit !== 'und' && <span className="text-ink-subtle"> / {i.unit_symbol}</span>}</span>
       ) },
       ...costCols, { key: 'stock', header: 'Existencia', align: 'right', cell: (i) => <Stock item={i} /> }, status]
    : [nameCell, category, { key: 'stock', header: 'Existencia', align: 'right', cell: (i) => <Stock item={i} /> },
       { key: 'min', header: 'Mínimo', align: 'right', hideOnMobile: true,
         cell: (i) => (Number(i.minimum_stock) > 0 ? formatQty(i.minimum_stock, i.unit_symbol) : <span className="text-ink-subtle">—</span>) },
       ...costCols, status]

  const Icon = copy.icon
  const emptyAction = !canManage ? undefined
    : group === 'ingredients' && isBakery
      ? { label: starter.isPending ? 'Cargando…' : 'Cargar ingredientes comunes de panadería', onClick: () => starter.mutate(),
          icon: <PackagePlus size={14} /> }
      : { label: `Agregar ${copy.noun}`, onClick: () => setEditing('new'), icon: <Plus size={14} /> }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <SearchInput label={copy.searchLabel} placeholder="Nombre o código" value={search} onChange={(v) => { setSearch(v); setPage(1) }} />
        <div className="sm:w-52">
          <Select aria-label="Filtro" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1) }}>
            <option value="">Todos</option>
            {group === 'products' && <>
              <option value="finished_good">Elaborados</option>
              <option value="resale">Reventa</option>
              <option value="service">Servicios</option>
            </>}
            <option value="low">Bajo el mínimo</option>
            <option value="active">Activos</option>
            <option value="inactive">Inactivos</option>
          </Select>
        </div>
        <div className="sm:ml-auto">
          {canManage && <Button icon={<Plus size={15} />} onClick={() => setEditing('new')}>{copy.newLabel}</Button>}
        </div>
      </div>

      <DataTable caption={copy.title} columns={columns} rows={data?.results} rowKey={(i) => i.id} isLoading={isLoading}
        pagination={{ data, onPageChange: setPage, noun: copy.plural, isFetching }}
        rowActions={(i) => canManage && (
          <RowActions name={i.name} onEdit={loadingId === i.id ? undefined : () => void openEdit(i)} onDelete={() => del.open(i)} />
        )}
        empty={search || filter
          ? <EmptyState icon={<Icon size={20} />} title="Sin resultados" description={`Ningún ${copy.noun} coincide con los filtros.`} />
          : <EmptyState icon={<Icon size={20} />} title={copy.emptyTitle}
                        description={group === 'ingredients' && isBakery && canManage
                          ? 'Empieza con los ingredientes más comunes (harina, huevos, queso costeño, empaques…) y luego registra su costo y existencia. O créalos uno por uno.'
                          : copy.emptyText}
                        action={emptyAction} />}
      />

      <Modal title={editing === 'new' ? copy.newLabel : `Editar ${copy.noun}`} isOpen={editing !== null} onClose={() => setEditing(null)} size="lg">
        {editing !== null && <ItemForm group={group} item={editing === 'new' ? undefined : editing}
                                       onSuccess={() => setEditing(null)} onCancel={() => setEditing(null)} />}
      </Modal>
      <ConfirmDialog isOpen={del.target !== null} title={`Eliminar ${copy.noun}`} confirmLabel="Eliminar"
                     description={<>Se eliminará <strong className="text-ink">{del.target?.name}</strong>. Si aparece en facturas no podrá
                       eliminarse; en ese caso desactívalo.</>}
                     loading={del.loading} error={del.error} onConfirm={del.confirm} onClose={del.close} />
    </div>
  )
}

function CategoriesTab({ group, canManage }: { group: ItemGroup; canManage: boolean }) {
  const copy = useCopy(group)
  const kind = copy.categoryKind
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Category | 'new' | null>(null)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['categories', kind, page], queryFn: () => catalogApi.listCategories({ kind, page }), placeholderData: (prev) => prev,
  })
  const del = useDeleteDialog<Category>((c) => catalogApi.deleteCategory(c.id), 'categories', (c) => `Categoría «${c.name}» eliminada`)

  const columns: Column<Category>[] = [
    { key: 'name', header: 'Categoría', primary: true, cell: (c) => <span className="font-medium">{c.name}</span> },
    { key: 'description', header: 'Descripción', hideOnMobile: true, cell: (c) => <span className="text-ink-muted">{c.description || '—'}</span> },
    { key: 'count', header: copy.title, align: 'right', cell: (c) => c.items_count },
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
        {editing !== null && <CategoryForm kind={kind} category={editing === 'new' ? undefined : editing}
                                           onSuccess={() => setEditing(null)} onCancel={() => setEditing(null)} />}
      </Modal>
      <ConfirmDialog isOpen={del.target !== null} title="Eliminar categoría" confirmLabel="Eliminar"
                     description={<>Se eliminará <strong className="text-ink">{del.target?.name}</strong>. Sus {copy.plural} quedarán sin categoría.</>}
                     loading={del.loading} error={del.error} onConfirm={del.confirm} onClose={del.close} />
    </div>
  )
}

/** Pantalla de catálogo compartida por Productos e Ingredientes (un único modelo Item en el backend). */
export default function CatalogScreen({ group }: { group: ItemGroup }) {
  const canManage = useCan()('catalog.manage')
  const [tab, setTab] = useState<'items' | 'categories'>('items')
  const copy = useCopy(group)
  return (
    <Page>
      <PageHeader title={copy.title} description={copy.description} />
      <Tabs label={`Secciones de ${copy.plural}`} value={tab} onChange={setTab}
            tabs={[{ id: 'items', label: copy.title }, { id: 'categories', label: 'Categorías' }]} />
      {tab === 'items' ? <ItemsTab key={group} group={group} canManage={canManage} />
        : <CategoriesTab key={group} group={group} canManage={canManage} />}
    </Page>
  )
}
