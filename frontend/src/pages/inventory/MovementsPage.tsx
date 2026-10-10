import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownLeft, ArrowUpRight, ClipboardCheck, History, Plus, Trash2 } from 'lucide-react'
import { inventoryApi, type StockMovement } from '@/api/inventory'
import ItemPicker, { type ItemOption } from '@/components/inventory/ItemPicker'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import Select from '@/components/ui/Select'
import { formatQty, formatUnitCost, isInbound } from '@/lib/catalog'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'

const TYPES: [string, string][] = [
  ['', 'Todos los movimientos'], ['purchase', 'Compras'], ['sale', 'Ventas'], ['sale_void', 'Anulaciones'],
  ['production_output', 'Producción'], ['production_consume', 'Consumo en producción'], ['waste', 'Mermas'],
  ['adjustment_in', 'Ajustes (sobrante)'], ['adjustment_out', 'Ajustes (faltante)'], ['opening', 'Saldos iniciales'],
]

interface CountRow { key: number; item: ItemOption | null; counted: string }
let nextKey = 1

/** Conteo físico: se escribe lo que hay en el estante y el sistema registra la diferencia. */
function CountForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient()
  const [rows, setRows] = useState<CountRow[]>([{ key: nextKey++, item: null, counted: '' }])
  const [note, setNote] = useState('')
  const set = (key: number, patch: Partial<CountRow>) => setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)))
  const valid = rows.filter((r) => r.item && r.counted !== '')
  const apply = useMutation({
    mutationFn: () => inventoryApi.count({ note, counts: valid.map((r) => ({ item: r.item!.id, counted: r.counted.replace(',', '.') })) }),
    onSuccess: (res) => {
      void queryClient.invalidateQueries({ queryKey: ['movements'] })
      void queryClient.invalidateQueries({ queryKey: ['items'] })
      toast.success(res.adjustments.length ? `${res.adjustments.length} ajuste(s) registrados` : 'Todo cuadró: no hubo ajustes')
      onDone()
    },
  })
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); apply.mutate() }}>
      <p className="text-sm text-ink-muted">Cuenta lo que hay físicamente en la sucursal principal. El sistema compara con su existencia y registra la diferencia como ajuste.</p>
      {rows.map((r) => (
        <div key={r.key} className="grid gap-2 sm:grid-cols-[1fr_160px_140px_40px] items-end">
          <ItemPicker label="Ítem" value={r.item} onChange={(item) => set(r.key, { item })} queryKey="count-items" params={{}} />
          <div className="pb-2 text-sm text-ink-muted">{r.item ? <>Sistema: <span className="num text-ink">{formatQty(r.item.item.stock, r.item.item.unit_symbol)}</span></> : null}</div>
          <Input label={`Contado${r.item ? ` (${r.item.item.unit_symbol})` : ''}`} inputMode="decimal" value={r.counted}
                 onChange={(e) => set(r.key, { counted: e.target.value })} />
          <button type="button" aria-label="Quitar" onClick={() => setRows((rs) => rs.filter((x) => x.key !== r.key))}
                  className="h-9 w-10 rounded-lg text-ink-subtle hover:text-danger hover:bg-danger-soft flex items-center justify-center"><Trash2 size={15} /></button>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" icon={<Plus size={14} />} onClick={() => setRows((rs) => [...rs, { key: nextKey++, item: null, counted: '' }])}>
        Agregar ítem
      </Button>
      <Input label="Nota" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ej.: conteo de cierre de mes" />
      {apply.isError && <Alert tone="danger">{getErrorMessage(apply.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" loading={apply.isPending} disabled={!valid.length}>Aplicar conteo</Button>
      </div>
    </form>
  )
}

export default function MovementsPage() {
  const can = useCan()
  const showCosts = can('catalog.view_costs')
  const [params] = useSearchParams()
  const [item, setItem] = useState<ItemOption | null>(null)
  const itemId = item?.id ?? (params.get('item') ? Number(params.get('item')) : undefined)
  const [type, setType] = useState('')
  const [page, setPage] = useState(1)
  const [counting, setCounting] = useState(false)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['movements', itemId, type, page], queryFn: () => inventoryApi.movements({ item: itemId, type: type || undefined, page }),
    placeholderData: (prev) => prev,
  })
  const columns: Column<StockMovement>[] = [
    { key: 'item', header: 'Ítem', primary: true, cell: (m) => (
      <div className="flex items-center gap-3">
        <span className={cn('w-7 h-7 rounded-lg flex items-center justify-center shrink-0', isInbound(m.type) ? 'bg-success-soft text-success' : 'bg-warning-soft text-warning')}>
          {isInbound(m.type) ? <ArrowDownLeft size={14} /> : <ArrowUpRight size={14} />}
        </span>
        <div className="min-w-0"><p className="font-medium text-ink truncate">{m.item_name}</p>
          <p className="text-xs text-ink-muted">{formatDateTime(m.created_at)}{m.created_by_name && ` · ${m.created_by_name}`}</p></div>
      </div>
    ) },
    { key: 'type', header: 'Movimiento', cell: (m) => <span>{m.type_label}<span className="block text-xs text-ink-muted">{m.source_label}{m.reason && m.reason !== m.source_label && ` · ${m.reason}`}</span></span> },
    { key: 'qty', header: 'Cantidad', align: 'right', cell: (m) => (
      <span className={cn('font-medium', isInbound(m.type) ? 'text-ink' : 'text-warning')}>{isInbound(m.type) ? '+' : '−'}{formatQty(Math.abs(Number(m.quantity)), m.unit_symbol)}</span>
    ) },
    { key: 'balance', header: 'Saldo', align: 'right', hideOnMobile: true, cell: (m) => formatQty(m.balance_after, m.unit_symbol) },
    ...(showCosts ? [
      { key: 'cost', header: 'Costo unit.', align: 'right' as const, hideOnMobile: true, cell: (m: StockMovement) => formatUnitCost(m.unit_cost) },
      { key: 'total', header: 'Valor', align: 'right' as const, cell: (m: StockMovement) => formatCOP(Math.abs(Number(m.total_cost))) },
      { key: 'avg', header: 'Promedio después', align: 'right' as const, hideOnMobile: true, cell: (m: StockMovement) => formatUnitCost(m.avg_cost_after) },
    ] : []),
  ]
  return (
    <Page>
      <PageHeader title="Movimientos de inventario" description="Cada entrada y salida, con su costo y su documento (kardex)"
                  actions={can('inventory.adjust') && <Button icon={<ClipboardCheck size={15} />} onClick={() => setCounting(true)}>Conteo físico</Button>} />
      <div className="grid gap-3 sm:grid-cols-[1fr_240px]">
        <ItemPicker value={item} onChange={(o) => { setItem(o); setPage(1) }} queryKey="kardex-items" params={{}} placeholder="Filtrar por ítem (kardex)" />
        <Select aria-label="Tipo de movimiento" value={type} onChange={(e) => { setType(e.target.value); setPage(1) }}>
          {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </Select>
      </div>
      <DataTable caption="Movimientos" columns={columns} rows={data?.results} rowKey={(m) => m.id} isLoading={isLoading}
        pagination={{ data, onPageChange: setPage, noun: 'movimientos', isFetching }}
        empty={<EmptyState icon={<History size={20} />} title="Sin movimientos" description="Compras, ventas, producción, mermas y ajustes aparecerán aquí." />} />
      <Modal title="Conteo físico" isOpen={counting} onClose={() => setCounting(false)} size="lg">
        {counting && <CountForm onDone={() => setCounting(false)} />}
      </Modal>
    </Page>
  )
}
