import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Banknote, CreditCard, Landmark, Plus, Smartphone, X } from 'lucide-react'
import { salesApi, type PaymentMethod, type Sale } from '@/api/pos'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import { cn } from '@/lib/cn'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { cartTotals, fromCents, newClientId, quickCashOptions, toCents, type CartLine } from '@/lib/pos'

const ICONS: Record<PaymentMethod['kind'], typeof Banknote> = {
  cash: Banknote, card: CreditCard, wallet: Smartphone, transfer: Landmark,
}

interface Row { methodId: number; amount: string }

// Montos como se escriben en Colombia: "20.000" o "20000" (punto de miles) y coma decimal
const parseAmount = (v: string) => v.replace(/\./g, '').replace(',', '.')
const toInput = (cents: number) => (cents % 100 === 0 ? String(cents / 100) : (cents / 100).toFixed(2).replace('.', ','))

export default function PaymentModal({ lines, customerId, methods, canDiscount, onClose, onPaid }: {
  lines: CartLine[]
  customerId: number | null
  methods: PaymentMethod[]
  canDiscount: boolean
  onClose: () => void
  onPaid: (sale: Sale) => void
}) {
  // Un identificador por intento de cobro: si se reintenta (doble clic, mala señal), el servidor no duplica la venta
  const [clientId] = useState(newClientId)
  const cashMethod = methods.find((m) => m.kind === 'cash') ?? methods[0]
  const [discount, setDiscount] = useState('')
  const totals = cartTotals(lines, parseAmount(discount))
  const [rows, setRows] = useState<Row[]>([{ methodId: cashMethod.id, amount: toInput(totals.total) }])

  const methodOf = (id: number) => methods.find((m) => m.id === id)!
  const tendered = rows.reduce((s, r) => s + toCents(parseAmount(r.amount) || 0), 0)
  const cashTendered = rows.filter((r) => methodOf(r.methodId).kind === 'cash')
    .reduce((s, r) => s + toCents(parseAmount(r.amount) || 0), 0)
  const missing = Math.max(totals.total - tendered, 0)
  const change = Math.max(tendered - totals.total, 0)
  const invalidChange = change > cashTendered
  const single = rows.length === 1

  const setRow = (i: number, patch: Partial<Row>) => setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)))
  const pickMethod = (method: PaymentMethod) => {
    // Con un solo pago, cambiar de medio cobra el total exacto por ese medio
    if (single) setRows([{ methodId: method.id, amount: toInput(totals.total) }])
  }

  const pay = useMutation({
    mutationFn: () => salesApi.create({
      client_uuid: clientId, customer: customerId,
      discount: canDiscount && discount ? parseAmount(discount) : undefined,
      lines: lines.map((l) => ({ item: l.itemId, quantity: l.quantity })),
      payments: rows.filter((r) => toCents(parseAmount(r.amount) || 0) > 0)
        .map((r) => ({ method: r.methodId, amount: parseAmount(r.amount) })),
    }),
    onSuccess: onPaid,
  })

  return (
    <Modal title="Cobrar" isOpen onClose={onClose} size="lg">
      <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); if (!missing && !invalidChange) pay.mutate() }}>
        <div className="flex items-end justify-between rounded-2xl bg-surface-muted/70 px-5 py-4">
          <div>
            <p className="text-xs font-medium text-ink-muted">Total a pagar</p>
            <p className="text-3xl font-semibold tracking-tight text-ink num">{formatCOP(fromCents(totals.total))}</p>
          </div>
          {totals.discount > 0 && <p className="text-xs text-ink-muted">Incluye descuento de {formatCOP(fromCents(totals.discount))}</p>}
        </div>

        {single && (
          <div role="radiogroup" aria-label="Medio de pago" className="grid grid-cols-3 sm:grid-cols-5 gap-2">
            {methods.map((m) => {
              const Icon = ICONS[m.kind]
              const active = rows[0].methodId === m.id
              return (
                <button key={m.id} type="button" role="radio" aria-checked={active} onClick={() => pickMethod(m)}
                        className={cn('h-16 rounded-xl border flex flex-col items-center justify-center gap-1 text-sm transition-colors',
                          active ? 'border-primary bg-primary-soft text-primary-ink font-medium' : 'border-line-strong text-ink hover:bg-surface-muted')}>
                  <Icon size={18} aria-hidden />{m.name}
                </button>
              )
            })}
          </div>
        )}

        <div className="space-y-3">
          {rows.map((row, i) => {
            const method = methodOf(row.methodId)
            return (
              <div key={i} className="flex items-end gap-2">
                {!single && (
                  <select aria-label="Medio de pago" value={row.methodId} onChange={(e) => setRow(i, { methodId: Number(e.target.value) })}
                          className="h-11 rounded-xl border border-line-strong bg-surface px-3 text-sm text-ink">
                    {methods.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                  </select>
                )}
                <div className="flex-1">
                  <Input label={method.kind === 'cash' ? 'Recibido en efectivo' : `Valor en ${method.name}`} inputMode="numeric"
                         className="h-11 text-lg num" value={row.amount} autoFocus={i === 0}
                         onChange={(e) => setRow(i, { amount: e.target.value })} />
                </div>
                {!single && (
                  <button type="button" aria-label="Quitar pago" onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}
                          className="h-11 w-11 rounded-xl text-ink-subtle hover:bg-surface-muted hover:text-danger flex items-center justify-center">
                    <X size={16} />
                  </button>
                )}
              </div>
            )
          })}
          {single && methodOf(rows[0].methodId).kind === 'cash' && (
            <div className="flex flex-wrap gap-2">
              {quickCashOptions(totals.total).map((cents, idx) => (
                <button key={cents} type="button" onClick={() => setRow(0, { amount: toInput(cents) })}
                        className="h-10 px-3.5 rounded-lg border border-line-strong text-sm text-ink hover:bg-surface-muted num">
                  {idx === 0 ? 'Exacto' : formatCOP(fromCents(cents))}
                </button>
              ))}
            </div>
          )}
          <button type="button" className="text-sm text-primary-ink hover:underline inline-flex items-center gap-1"
                  onClick={() => setRows((rs) => [...rs, { methodId: (methods.find((m) => m.kind !== 'cash') ?? cashMethod).id,
                                                           amount: toInput(missing) }])}>
            <Plus size={14} /> Pagar con varios medios
          </button>
        </div>

        {canDiscount && (
          <Input label="Descuento (opcional)" inputMode="numeric" placeholder="0" value={discount}
                 onChange={(e) => {
                   setDiscount(e.target.value)
                   // Con un solo pago, el valor a cobrar sigue al nuevo total
                   if (single) setRow(0, { amount: toInput(cartTotals(lines, parseAmount(e.target.value)).total) })
                 }} hint="Valor en pesos sobre el total." />
        )}

        <div className={cn('rounded-xl px-5 py-3 flex items-center justify-between',
          missing ? 'bg-warning-soft text-warning' : change ? 'bg-success-soft text-success' : 'bg-surface-muted text-ink-muted')}>
          <span className="text-sm font-medium">{missing ? 'Falta' : change ? 'Cambio a entregar' : 'Pago exacto'}</span>
          <span className="text-2xl font-semibold num">{formatCOP(fromCents(missing || change))}</span>
        </div>
        {invalidChange && <Alert tone="warning">Solo el efectivo puede superar el total para dar cambio.</Alert>}
        {pay.isError && <Alert tone="danger">{getErrorMessage(pay.error)}</Alert>}

        <Button type="submit" size="lg" fullWidth loading={pay.isPending} disabled={missing > 0 || invalidChange}
                className="h-14 text-lg">
          Confirmar pago
        </Button>
      </form>
    </Modal>
  )
}
