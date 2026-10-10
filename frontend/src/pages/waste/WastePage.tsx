import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Flame } from 'lucide-react'
import { wasteApi, type WasteRecord } from '@/api/inventory'
import ItemPicker, { type ItemOption } from '@/components/inventory/ItemPicker'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import { Card, CardHeader } from '@/components/ui/Card'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import { formatQty } from '@/lib/catalog'
import { cn } from '@/lib/cn'
import { formatDateTime, todayISO } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'

/** Registro en pocos toques: qué, cuánto y por qué. */
function WasteForm() {
  const queryClient = useQueryClient()
  const reasons = useQuery({ queryKey: ['waste-reasons'], queryFn: wasteApi.reasons, staleTime: 300_000 })
  const [item, setItem] = useState<ItemOption | null>(null)
  const [quantity, setQuantity] = useState('')
  const [reason, setReason] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const save = useMutation({
    mutationFn: () => wasteApi.create({ item: item!.id, quantity: quantity.replace(',', '.'), reason: reason!, notes }),
    onSuccess: (r) => {
      void queryClient.invalidateQueries({ queryKey: ['waste'] })
      void queryClient.invalidateQueries({ queryKey: ['items'] })
      toast.success(`Merma registrada: ${formatQty(r.quantity, r.unit_symbol)} de ${r.item_name}`)
      setItem(null); setQuantity(''); setNotes('')
    },
  })
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
      <div className="grid sm:grid-cols-[1fr_160px] gap-4">
        <ItemPicker label="¿Qué se perdió?" value={item} onChange={setItem} queryKey="waste-items" params={{}}
                    placeholder="Pan de bono, harina…" />
        <Input label={`Cantidad${item ? ` (${item.item.unit_symbol})` : ''}`} inputMode="decimal" value={quantity}
               onChange={(e) => setQuantity(e.target.value)} />
      </div>
      <fieldset>
        <legend className="text-sm font-medium text-ink mb-2">Motivo</legend>
        <div role="radiogroup" className="flex flex-wrap gap-2">
          {reasons.data?.map((r) => (
            <button key={r.id} type="button" role="radio" aria-checked={reason === r.id} onClick={() => setReason(r.id)}
                    className={cn('h-10 px-4 rounded-full text-sm border transition-colors',
                      reason === r.id ? 'bg-ink text-canvas border-ink' : 'border-line-strong text-ink hover:bg-surface-muted')}>
              {r.name}
            </button>
          ))}
        </div>
      </fieldset>
      <Input label="Nota (opcional)" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Ej.: tanda de las 6 a. m." />
      {save.isError && <Alert tone="danger">{getErrorMessage(save.error)}</Alert>}
      <div className="flex justify-end">
        <Button type="submit" size="lg" loading={save.isPending} disabled={!item || !(Number(quantity.replace(',', '.')) > 0) || !reason}>
          Registrar merma
        </Button>
      </div>
    </form>
  )
}

export default function WastePage() {
  const can = useCan()
  const canView = can('waste.view')
  const [page, setPage] = useState(1)
  const [from, setFrom] = useState(todayISO())
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['waste', page, from], queryFn: () => wasteApi.list({ page, date_from: from || undefined }),
    placeholderData: (prev) => prev, enabled: canView,
  })
  const columns: Column<WasteRecord>[] = [
    { key: 'item', header: 'Ítem', primary: true, cell: (r) => (
      <div><p className="font-medium text-ink">{r.item_name}</p><p className="text-xs text-ink-muted">{formatDateTime(r.created_at)} · {r.created_by_name}</p></div>
    ) },
    { key: 'qty', header: 'Cantidad', align: 'right', cell: (r) => formatQty(r.quantity, r.unit_symbol) },
    { key: 'reason', header: 'Motivo', cell: (r) => <span>{r.reason_name}{r.notes && <span className="block text-xs text-ink-muted">{r.notes}</span>}</span> },
    ...(can('catalog.view_costs') ? [{ key: 'cost', header: 'Costo', align: 'right' as const, cell: (r: WasteRecord) => formatCOP(r.total_cost) }] : []),
  ]
  return (
    <Page>
      <PageHeader title="Mermas" description="Lo que se pierde también es costo: regístralo para saber cuánto y por qué" />
      {can('waste.register') && <Card><CardHeader title="Registrar merma" /><div className="px-5 pb-5"><WasteForm /></div></Card>}
      {canView && (
        <>
          <div className="flex flex-col sm:flex-row sm:items-end gap-3 justify-between">
            <div className="sm:w-48"><Input label="Desde" type="date" value={from} onChange={(e) => { setFrom(e.target.value); setPage(1) }} /></div>
            {data?.total_cost !== undefined && (
              <p className="text-sm text-ink-muted">Costo de las mermas en el período: <strong className="text-ink num">{formatCOP(data.total_cost)}</strong></p>
            )}
          </div>
          <DataTable caption="Mermas" columns={columns} rows={data?.results} rowKey={(r) => r.id} isLoading={isLoading}
            pagination={{ data, onPageChange: setPage, noun: 'mermas', isFetching }}
            empty={<EmptyState compact icon={<Flame size={20} />} title="Sin mermas en este período" />} />
        </>
      )}
    </Page>
  )
}
