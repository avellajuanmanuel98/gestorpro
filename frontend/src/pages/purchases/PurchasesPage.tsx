import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { PackagePlus, Plus, Trash2, Truck } from 'lucide-react'
import { catalogApi } from '@/api/catalog'
import { purchasesApi, type PurchaseSummary } from '@/api/inventory'
import { suppliersApi } from '@/api/suppliers'
import ItemPicker, { type ItemOption } from '@/components/inventory/ItemPicker'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Combobox, { type ComboOption } from '@/components/ui/Combobox'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import SearchInput from '@/components/ui/SearchInput'
import { SkeletonText } from '@/components/ui/Skeleton'
import { compatibleUnits, formatQty, formatUnitCost } from '@/lib/catalog'
import { formatDate, todayISO } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'

interface Line { key: number; item: ItemOption | null; quantity: string; unit: string; unitCost: string }
let nextKey = 1
const emptyLine = (): Line => ({ key: nextKey++, item: null, quantity: '', unit: '', unitCost: '' })
const num = (v: string) => v.replace(/\./g, '').replace(',', '.')

async function searchSuppliers(term: string): Promise<ComboOption[]> {
  const res = await suppliersApi.list({ search: term || undefined, page_size: 15 })
  return res.results.map((s) => ({ id: s.id, label: s.company_name, description: s.document_number || undefined }))
}

function PurchaseForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient()
  const units = useQuery({ queryKey: ['units'], queryFn: catalogApi.units, staleTime: Infinity })
  const [supplier, setSupplier] = useState<ComboOption | null>(null)
  const [invoice, setInvoice] = useState('')
  const [date, setDate] = useState(todayISO())
  const [lines, setLines] = useState<Line[]>([emptyLine()])
  const set = (key: number, patch: Partial<Line>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)))
  const lineTotal = (l: Line) => (Number(num(l.quantity)) || 0) * (Number(num(l.unitCost)) || 0)
  const total = lines.reduce((sum, l) => sum + lineTotal(l), 0)
  const ready = lines.length > 0 && lines.every((l) => l.item && Number(num(l.quantity)) > 0 && l.unitCost !== '')

  const save = useMutation({
    mutationFn: () => purchasesApi.create({
      supplier: supplier?.id ?? null, supplier_invoice: invoice, received_on: date,
      lines: lines.map((l) => ({ item: l.item!.id, quantity: num(l.quantity), unit: l.unit || l.item!.item.unit,
                                 unit_cost: num(l.unitCost) })),
    }),
    onSuccess: (p) => {
      void queryClient.invalidateQueries({ queryKey: ['purchases'] })
      void queryClient.invalidateQueries({ queryKey: ['items'] })
      toast.success(`Compra ${p.number} registrada: existencias y costos actualizados`)
      onDone()
    },
  })

  return (
    <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); if (ready) save.mutate() }}>
      <div className="grid sm:grid-cols-3 gap-4">
        <Combobox label="Proveedor" value={supplier} onChange={setSupplier} search={searchSuppliers} queryKey="purchase-suppliers"
                  placeholder="Opcional" />
        <Input label="N.º de factura del proveedor" value={invoice} onChange={(e) => setInvoice(e.target.value)} />
        <Input label="Fecha de recepción" type="date" required value={date} onChange={(e) => setDate(e.target.value)} />
      </div>

      <div className="space-y-3">
        {lines.map((l) => {
          const options = l.item && units.data ? compatibleUnits(units.data, l.item.item.unit) : []
          return (
            <div key={l.key} className="grid gap-2 sm:grid-cols-[1fr_110px_120px_140px_110px_40px] items-end rounded-xl border border-line p-3">
              <ItemPicker label="Ítem" value={l.item} queryKey="purchase-items" params={{}} placeholder="Harina, huevos, gaseosa…"
                          onChange={(item) => set(l.key, { item, unit: item?.item.unit ?? '' })} />
              <Input label="Cantidad" inputMode="decimal" value={l.quantity} onChange={(e) => set(l.key, { quantity: e.target.value })} />
              <label className="space-y-1.5 text-sm">
                <span className="font-medium text-ink">Unidad</span>
                <select value={l.unit} onChange={(e) => set(l.key, { unit: e.target.value })} disabled={!l.item}
                        className="w-full h-9 rounded-lg border border-line-strong bg-surface px-2 text-sm text-ink">
                  {options.map((u) => <option key={u.code} value={u.code}>{u.name}</option>)}
                </select>
              </label>
              <Input label={`Costo por ${options.find((u) => u.code === l.unit)?.symbol ?? 'unidad'}`} inputMode="decimal"
                     value={l.unitCost} onChange={(e) => set(l.key, { unitCost: e.target.value })} />
              <div className="text-right pb-2"><p className="text-xs text-ink-muted">Total</p><p className="text-sm font-medium num">{formatCOP(lineTotal(l))}</p></div>
              <button type="button" aria-label="Quitar línea" onClick={() => setLines((ls) => ls.filter((x) => x.key !== l.key))}
                      className="h-9 w-10 rounded-lg text-ink-subtle hover:text-danger hover:bg-danger-soft flex items-center justify-center"><Trash2 size={15} /></button>
            </div>
          )
        })}
        <Button type="button" variant="outline" size="sm" icon={<Plus size={14} />} onClick={() => setLines((ls) => [...ls, emptyLine()])}>
          Agregar ítem
        </Button>
      </div>

      <div className="flex items-center justify-between rounded-xl bg-surface-muted/70 px-5 py-3">
        <span className="text-sm text-ink-muted">Total de la compra (lo confirma el servidor)</span>
        <span className="text-xl font-semibold num text-ink">{formatCOP(total)}</span>
      </div>
      {save.isError && <Alert tone="danger">{getErrorMessage(save.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" loading={save.isPending} disabled={!ready}>Registrar compra</Button>
      </div>
    </form>
  )
}

function PurchaseDetail({ id }: { id: number }) {
  const { data } = useQuery({ queryKey: ['purchase', id], queryFn: () => purchasesApi.get(id) })
  if (!data) return <SkeletonText lines={6} />
  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-muted">{data.supplier_name ?? 'Sin proveedor'}{data.supplier_invoice && ` · Factura ${data.supplier_invoice}`} ·
        {' '}{formatDate(data.received_on)} · {data.created_by_name}</p>
      <div className="rounded-lg border border-line overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-muted/60 text-xs text-ink-muted"><tr>
            <th className="text-left px-3 py-2 font-medium">Ítem</th><th className="text-right px-3 py-2 font-medium">Comprado</th>
            <th className="text-right px-3 py-2 font-medium">Entró al inventario</th><th className="text-right px-3 py-2 font-medium">Total</th></tr></thead>
          <tbody className="divide-y divide-line">
            {data.lines.map((l) => (
              <tr key={l.id}>
                <td className="px-3 py-2 text-ink">{l.item_name}</td>
                <td className="px-3 py-2 text-right num">{formatQty(l.quantity, l.unit_symbol)} × {formatUnitCost(l.unit_cost)}</td>
                <td className="px-3 py-2 text-right num">{formatQty(l.base_quantity, l.item_unit_symbol)}
                  <span className="block text-[11px] text-ink-subtle">{formatUnitCost(l.base_unit_cost)} / {l.item_unit_symbol}</span></td>
                <td className="px-3 py-2 text-right num">{formatCOP(l.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-right text-base font-semibold num">Total {formatCOP(data.total)}</p>
    </div>
  )
}

export default function PurchasesPage() {
  const canCreate = useCan()('purchases.create')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [creating, setCreating] = useState(false)
  const [open, setOpen] = useState<PurchaseSummary | null>(null)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['purchases', page, search], queryFn: () => purchasesApi.list({ page, search: search || undefined }),
    placeholderData: (prev) => prev,
  })
  const columns: Column<PurchaseSummary>[] = [
    { key: 'number', header: 'Compra', primary: true, cell: (p) => (
      <div><p className="font-medium text-ink">{p.number}</p><p className="text-xs text-ink-muted">{formatDate(p.received_on)}</p></div>
    ) },
    { key: 'supplier', header: 'Proveedor', cell: (p) => p.supplier_name ?? <span className="text-ink-subtle">—</span> },
    { key: 'invoice', header: 'Factura', hideOnMobile: true, cell: (p) => p.supplier_invoice || <span className="text-ink-subtle">—</span> },
    { key: 'lines', header: 'Ítems', align: 'right', hideOnMobile: true, cell: (p) => p.lines_count },
    { key: 'total', header: 'Total', align: 'right', cell: (p) => <span className="font-medium">{formatCOP(p.total)}</span> },
  ]
  return (
    <Page>
      <PageHeader title="Compras" description="Mercancía recibida: sube las existencias y actualiza el costo promedio"
                  actions={canCreate && <Button icon={<PackagePlus size={15} />} onClick={() => setCreating(true)}>Registrar compra</Button>} />
      <SearchInput label="Buscar compras" placeholder="Número, factura o proveedor" value={search} onChange={(v) => { setSearch(v); setPage(1) }} />
      <DataTable caption="Compras" columns={columns} rows={data?.results} rowKey={(p) => p.id} isLoading={isLoading}
        onRowClick={setOpen} pagination={{ data, onPageChange: setPage, noun: 'compras', isFetching }}
        empty={<EmptyState icon={<Truck size={20} />} title="Aún no hay compras"
                           description="Registra lo que te llega de los proveedores: así el sistema conoce el costo real de cada ingrediente."
                           action={canCreate ? { label: 'Registrar compra', onClick: () => setCreating(true) } : undefined} />} />
      <Modal title="Registrar compra" isOpen={creating} onClose={() => setCreating(false)} size="xl">
        {creating && <PurchaseForm onDone={() => setCreating(false)} />}
      </Modal>
      <Modal title={open ? `Compra ${open.number}` : ''} isOpen={open !== null} onClose={() => setOpen(null)} size="lg">
        {open && <PurchaseDetail id={open.id} />}
      </Modal>
    </Page>
  )
}
