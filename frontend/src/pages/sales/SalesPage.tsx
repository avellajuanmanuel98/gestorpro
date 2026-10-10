import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Printer, Receipt as ReceiptIcon } from 'lucide-react'
import { salesApi, type SaleSummary } from '@/api/pos'
import Receipt from '@/components/pos/Receipt'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import SearchInput from '@/components/ui/SearchInput'
import Select from '@/components/ui/Select'
import { SkeletonText } from '@/components/ui/Skeleton'
import StatusMark from '@/components/ui/StatusMark'
import Textarea from '@/components/ui/Textarea'
import { formatQty } from '@/lib/catalog'
import { formatDateTime, formatTime, todayISO } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { SALE_STATUS } from '@/lib/status'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'

function SaleDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const queryClient = useQueryClient()
  const { data: sale, isLoading } = useQuery({ queryKey: ['sale', id], queryFn: () => salesApi.get(id) })
  const [voiding, setVoiding] = useState(false)
  const [reason, setReason] = useState('')
  const voidSale = useMutation({
    mutationFn: () => salesApi.void(id, reason),
    onSuccess: (s) => {
      queryClient.setQueryData(['sale', id], s)
      void queryClient.invalidateQueries({ queryKey: ['sales'] })
      void queryClient.invalidateQueries({ queryKey: ['cash-current'] })
      setVoiding(false)
      toast.success(`Venta ${s.number} anulada`)
    },
  })

  if (isLoading || !sale) return <SkeletonText lines={8} />
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-lg font-semibold text-ink">{sale.number}</p>
          <p className="text-sm text-ink-muted">{formatDateTime(sale.created_at)} · {sale.register_name} · {sale.cashier_name}</p>
          <p className="text-sm text-ink-muted">Cliente: {sale.customer_name}</p>
        </div>
        <StatusMark status={SALE_STATUS[sale.status]} />
      </div>
      {sale.status === 'voided' && (
        <Alert tone="danger">Anulada por {sale.voided_by_name} el {formatDateTime(sale.voided_at)}: {sale.void_reason}</Alert>
      )}
      <div className="rounded-lg border border-line overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-muted/60 text-xs text-ink-muted">
            <tr><th className="text-left px-3 py-2 font-medium">Producto</th><th className="text-right px-3 py-2 font-medium">Cant.</th>
              <th className="text-right px-3 py-2 font-medium">Total</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {sale.lines.map((l) => (
              <tr key={l.id}>
                <td className="px-3 py-2 text-ink">{l.item_name}<span className="block text-[11px] text-ink-subtle">{formatCOP(l.unit_price)} c/u{Number(l.tax_rate) > 0 && ` · IVA ${Number(l.tax_rate)} %`}</span></td>
                <td className="px-3 py-2 text-right num">{formatQty(l.quantity, l.unit_symbol)}</td>
                <td className="px-3 py-2 text-right num">{formatCOP(l.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <dl className="ml-auto max-w-xs space-y-1 text-sm">
        <div className="flex justify-between text-ink-muted"><dt>Subtotal</dt><dd className="num">{formatCOP(sale.subtotal)}</dd></div>
        {Number(sale.tax_total) > 0 && <div className="flex justify-between text-ink-muted"><dt>IVA</dt><dd className="num">{formatCOP(sale.tax_total)}</dd></div>}
        {Number(sale.discount) > 0 && <div className="flex justify-between text-ink-muted"><dt>Descuento</dt><dd className="num">−{formatCOP(sale.discount)}</dd></div>}
        <div className="flex justify-between font-semibold text-ink pt-1 border-t border-line"><dt>Total</dt><dd className="num">{formatCOP(sale.total)}</dd></div>
        {sale.payments.map((p) => (
          <div key={p.id} className="flex justify-between text-ink-muted"><dt>{p.method_name}</dt><dd className="num">{formatCOP(p.tendered)}</dd></div>
        ))}
        {Number(sale.change_given) > 0 && <div className="flex justify-between text-ink-muted"><dt>Cambio</dt><dd className="num">{formatCOP(sale.change_given)}</dd></div>}
      </dl>

      <div className="print-only"><Receipt sale={sale} /></div>
      {voiding ? (
        <form className="space-y-3 rounded-xl border border-danger/40 bg-danger-soft/40 p-4"
              onSubmit={(e) => { e.preventDefault(); voidSale.mutate() }}>
          <p className="text-sm text-ink">Se devolverá el efectivo de la caja y las existencias. La venta queda registrada como anulada.</p>
          <Textarea label="Motivo de la anulación" required rows={2} autoFocus value={reason} onChange={(e) => setReason(e.target.value)} />
          {voidSale.isError && <Alert tone="danger">{getErrorMessage(voidSale.error)}</Alert>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setVoiding(false)}>Cancelar</Button>
            <Button type="submit" variant="danger" loading={voidSale.isPending} disabled={!reason.trim()}>Anular venta</Button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap justify-end gap-2">
          {sale.can_void && <Button variant="outline" onClick={() => setVoiding(true)}>Anular</Button>}
          <Button variant="outline" icon={<Printer size={15} />} onClick={() => window.print()}>Reimprimir ticket</Button>
          <Button onClick={onClose}>Cerrar</Button>
        </div>
      )}
    </div>
  )
}

export default function SalesPage() {
  const can = useCan()
  const [date, setDate] = useState(todayISO())
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState<number | null>(null)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['sales', date, status, search, page],
    queryFn: () => salesApi.list({ date: date || undefined, status: status || undefined, search: search || undefined, page }),
    placeholderData: (prev) => prev,
  })

  const columns: Column<SaleSummary>[] = [
    { key: 'number', header: 'Venta', primary: true, cell: (s) => (
      <div><p className="font-medium text-ink">{s.number}</p><p className="text-xs text-ink-muted">{formatTime(s.created_at)}</p></div>
    ) },
    ...(can('sales.view_all') ? [{ key: 'cashier', header: 'Cajero', hideOnMobile: true, cell: (s: SaleSummary) => s.cashier_name }] : []),
    { key: 'customer', header: 'Cliente', hideOnMobile: true, cell: (s) => s.customer_name },
    { key: 'payment', header: 'Pago', cell: (s) => <span className="text-ink-muted">{s.payment_summary}</span> },
    { key: 'total', header: 'Total', align: 'right', cell: (s) => (
      <span className={s.status === 'voided' ? 'line-through text-ink-subtle' : 'font-medium'}>{formatCOP(s.total)}</span>
    ) },
    { key: 'status', header: 'Estado', cell: (s) => <StatusMark status={SALE_STATUS[s.status]} /> },
  ]

  return (
    <Page>
      <PageHeader title="Ventas" description={can('sales.view_all') ? 'Ventas del punto de venta de todo el equipo' : 'Tus ventas en el punto de venta'} />
      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput label="Buscar ventas" placeholder="Número o cliente" value={search} onChange={(v) => { setSearch(v); setPage(1) }} />
        <div className="sm:w-44"><Input type="date" aria-label="Fecha" value={date} onChange={(e) => { setDate(e.target.value); setPage(1) }} /></div>
        <div className="sm:w-44">
          <Select aria-label="Estado" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
            <option value="">Todas</option><option value="completed">Completadas</option><option value="voided">Anuladas</option>
          </Select>
        </div>
      </div>
      <DataTable caption="Ventas" columns={columns} rows={data?.results} rowKey={(s) => s.id} isLoading={isLoading}
        onRowClick={(s) => setOpen(s.id)}
        pagination={{ data, onPageChange: setPage, noun: 'ventas', isFetching }}
        empty={<EmptyState icon={<ReceiptIcon size={20} />} title="Sin ventas"
                           description={date ? 'No hay ventas en esta fecha con esos filtros.' : 'Aún no hay ventas registradas.'} />} />
      <Modal title="Detalle de la venta" isOpen={open !== null} onClose={() => setOpen(null)} size="lg">
        {open !== null && <SaleDetail id={open} onClose={() => setOpen(null)} />}
      </Modal>
    </Page>
  )
}
