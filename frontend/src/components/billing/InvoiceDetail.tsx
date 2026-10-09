import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { billingApi } from '@/api/billing'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { SkeletonText } from '@/components/ui/Skeleton'
import { formatDate } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { INVOICE_STATUS } from '@/lib/status'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'
import type { Invoice } from '@/types'
import { StatusStamp } from '@/components/ui/StatusMark'

type Status = Invoice['status']

// Transiciones que ofrece la interfaz (el backend bloquea cambios económicos en pagadas/canceladas)
const TRANSITIONS: Record<Status, { to: Status; label: string; variant: 'primary' | 'outline' | 'danger' }[]> = {
  draft: [{ to: 'sent', label: 'Marcar como enviada', variant: 'outline' }, { to: 'paid', label: 'Registrar pago', variant: 'primary' }],
  sent: [{ to: 'paid', label: 'Registrar pago', variant: 'primary' }, { to: 'overdue', label: 'Marcar vencida', variant: 'outline' }],
  overdue: [{ to: 'paid', label: 'Registrar pago', variant: 'primary' }],
  paid: [],
  cancelled: [],
}

export default function InvoiceDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const queryClient = useQueryClient()
  const can = useCan()
  const [confirm, setConfirm] = useState<'cancel' | 'delete' | null>(null)
  const { data: invoice, isLoading } = useQuery({ queryKey: ['invoice', id], queryFn: () => billingApi.get(id) })

  const refresh = () => {
    for (const key of ['invoices', 'invoice', 'billing-summary', 'recent-invoices', 'monthly-revenue']) {
      queryClient.invalidateQueries({ queryKey: [key] })
    }
  }
  const setStatus = useMutation({
    mutationFn: (status: Status) => billingApi.update(id, { status }),
    onSuccess: (inv) => { refresh(); setConfirm(null); toast.success(`${inv.number}: ${INVOICE_STATUS[inv.status].label.toLowerCase()}`) },
  })
  const remove = useMutation({
    mutationFn: () => billingApi.delete(id),
    onSuccess: () => { refresh(); toast.success('Documento eliminado'); onClose() },
  })

  if (isLoading || !invoice) return <SkeletonText lines={6} />
  const status = INVOICE_STATUS[invoice.status]
  const isQuote = invoice.invoice_type === 'quote'
  const canUpdate = can('billing.update')
  const deletable = can('billing.delete') && (isQuote || invoice.status === 'draft')

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-ink-muted">{isQuote ? 'Cotización' : 'Factura'}</p>
          <p className="text-lg font-semibold text-ink">{invoice.number}</p>
          <p className="text-sm text-ink-muted">{invoice.customer_name}</p>
        </div>
        <StatusStamp status={status} className="mt-1" />
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div><dt className="text-xs text-ink-muted">Emisión</dt><dd className="text-ink">{formatDate(invoice.issue_date)}</dd></div>
        <div><dt className="text-xs text-ink-muted">Vencimiento</dt><dd className="text-ink">{formatDate(invoice.due_date)}</dd></div>
      </dl>

      <div className="rounded-lg border border-line overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-muted/60 text-xs text-ink-muted">
            <tr><th className="text-left px-3 py-2 font-medium">Producto</th><th className="text-right px-3 py-2 font-medium">Cant.</th>
              <th className="text-right px-3 py-2 font-medium">Precio</th><th className="text-right px-3 py-2 font-medium">Total</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {invoice.lines.map((l) => (
              <tr key={l.id}>
                <td className="px-3 py-2 text-ink">{l.product_name}<span className="block text-[11px] text-ink-subtle">IVA {Number(l.tax_rate)} %</span></td>
                <td className="px-3 py-2 text-right num">{Number(l.quantity).toLocaleString('es-CO')}</td>
                <td className="px-3 py-2 text-right num">{formatCOP(l.unit_price)}</td>
                <td className="px-3 py-2 text-right num text-ink">{formatCOP(l.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <dl className="text-sm space-y-1.5 ml-auto max-w-xs">
        <div className="flex justify-between text-ink-muted"><dt>Subtotal</dt><dd className="num">{formatCOP(invoice.subtotal)}</dd></div>
        <div className="flex justify-between text-ink-muted"><dt>Impuestos</dt><dd className="num">{formatCOP(invoice.tax_amount)}</dd></div>
        {Number(invoice.discount) > 0 && (
          <div className="flex justify-between text-ink-muted"><dt>Descuento</dt><dd className="num">−{formatCOP(invoice.discount)}</dd></div>
        )}
        <div className="flex justify-between pt-1.5 border-t border-line font-semibold text-ink"><dt>Total</dt><dd className="num">{formatCOP(invoice.total)}</dd></div>
      </dl>

      {invoice.notes && <p className="text-sm text-ink-muted whitespace-pre-line">{invoice.notes}</p>}
      {setStatus.isError && <Alert>{getErrorMessage(setStatus.error)}</Alert>}

      {(canUpdate || deletable) && (
        <div className="flex flex-wrap justify-end gap-2 pt-2 border-t border-line">
          {deletable && <Button variant="ghost" className="text-danger mr-auto" onClick={() => setConfirm('delete')}>Eliminar</Button>}
          {canUpdate && !isQuote && !['paid', 'cancelled'].includes(invoice.status) && (
            <Button variant="ghost" onClick={() => setConfirm('cancel')}>Anular</Button>
          )}
          {canUpdate && !isQuote && TRANSITIONS[invoice.status].map((t) => (
            <Button key={t.to} variant={t.variant} loading={setStatus.isPending && setStatus.variables === t.to}
                    onClick={() => setStatus.mutate(t.to)}>{t.label}</Button>
          ))}
        </div>
      )}

      <ConfirmDialog isOpen={confirm !== null}
                     title={confirm === 'delete' ? 'Eliminar documento' : 'Anular factura'}
                     confirmLabel={confirm === 'delete' ? 'Eliminar' : 'Anular'}
                     description={confirm === 'delete'
                       ? <>Se eliminará <strong className="text-ink">{invoice.number}</strong> de forma definitiva.</>
                       : <>La factura <strong className="text-ink">{invoice.number}</strong> quedará anulada. Ya no podrá modificarse
                           y dejará de contar como cartera por cobrar. Quedará registrado en la auditoría.</>}
                     loading={remove.isPending || setStatus.isPending}
                     error={remove.isError ? getErrorMessage(remove.error) : null}
                     onConfirm={() => (confirm === 'delete' ? remove.mutate() : setStatus.mutate('cancelled'))}
                     onClose={() => setConfirm(null)} />
    </div>
  )
}
