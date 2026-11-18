import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Banknote, CreditCard, Delete, Landmark, Plus, Smartphone, X } from 'lucide-react'
import { salesApi, type PaymentMethod, type Sale } from '@/api/pos'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import { cn } from '@/lib/cn'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { cartTotals, fromCents, CASH_BILLS, newClientId, pressKey, receivedAfterBill, toCents, type CartLine, type PadKey } from '@/lib/pos'

// Teclado numérico en pantalla: para escribir lo recibido con clics (o con el dedo en pantalla táctil)
const PAD: { key: PadKey; label: React.ReactNode; aria: string }[] = [
  ...['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((d) => ({ key: d as PadKey, label: d, aria: d })),
  { key: '000', label: '000', aria: 'tres ceros' },
  { key: '0', label: '0', aria: '0' },
  { key: 'back', label: <Delete size={20} aria-hidden />, aria: 'Borrar el último número' },
]

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
  // true mientras lo recibido es el valor que propuso el sistema (el total exacto): el primer billete
  // tocado lo reemplaza; los siguientes se suman
  const [proposed, setProposed] = useState(true)
  // Pago que recibe lo que se escribe con el teclado en pantalla (el último campo tocado)
  const [active, setActive] = useState(0)

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
    if (single) {
      setRows([{ methodId: method.id, amount: toInput(totals.total) }])
      setProposed(true)
    }
  }
  const tapBill = (bill: number) => {
    setRow(0, { amount: toInput(receivedAfterBill(toCents(parseAmount(rows[0].amount) || 0), bill, proposed)) })
    setProposed(false)
  }
  const setExact = () => { setRow(0, { amount: toInput(totals.total) }); setProposed(true) }
  const tapKey = (key: PadKey) => {
    const i = Math.min(active, rows.length - 1)
    setRow(i, { amount: pressKey(rows[i].amount.replace(/\./g, ''), key, single && proposed) })
    setProposed(false)
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

  const cashSingle = single && methodOf(rows[0].methodId).kind === 'cash'

  return (
    <Modal title="Cobrar" isOpen onClose={onClose} size="xl">
      <form className="grid gap-x-6 gap-y-4 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]"
            onSubmit={(e) => { e.preventDefault(); if (!missing && !invalidChange) pay.mutate() }}>
        {/* Izquierda: total, medio de pago, lo recibido, el cambio y confirmar */}
        <div className="space-y-3.5 min-w-0">
          <div className="flex items-end justify-between rounded-2xl bg-surface-muted/70 px-5 py-3">
            <div>
              <p className="text-xs font-medium text-ink-muted">Total a pagar</p>
              <p className="text-3xl font-semibold tracking-tight text-ink num">{formatCOP(fromCents(totals.total))}</p>
            </div>
            {totals.discount > 0 && <p className="text-xs text-ink-muted">Incluye descuento de {formatCOP(fromCents(totals.discount))}</p>}
          </div>

          {single && (
            <div role="radiogroup" aria-label="Medio de pago" className="grid grid-cols-5 gap-2">
              {methods.map((m) => {
                const Icon = ICONS[m.kind]
                const on = rows[0].methodId === m.id
                return (
                  <button key={m.id} type="button" role="radio" aria-checked={on} onClick={() => pickMethod(m)}
                          className={cn('h-14 rounded-xl border flex flex-col items-center justify-center gap-0.5 text-xs transition-colors',
                            on ? 'border-primary bg-primary-soft text-primary-ink font-medium' : 'border-line-strong text-ink hover:bg-surface-muted')}>
                    <Icon size={17} aria-hidden /><span className="truncate max-w-full px-1">{m.name}</span>
                  </button>
                )
              })}
            </div>
          )}

          <div className="space-y-2">
            {rows.map((row, i) => {
              const method = methodOf(row.methodId)
              return (
                <div key={i} className="flex items-end gap-2">
                  {!single && (
                    <select aria-label="Medio de pago" value={row.methodId} onChange={(e) => setRow(i, { methodId: Number(e.target.value) })}
                            className="h-12 rounded-xl border border-line-strong bg-surface px-3 text-sm text-ink">
                      {methods.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                    </select>
                  )}
                  <div className="flex-1">
                    <Input label={method.kind === 'cash' ? 'Recibido en efectivo' : `Valor en ${method.name}`} inputMode="numeric"
                           className={cn('h-12 text-xl num', !single && active === i && 'border-primary')} value={row.amount} autoFocus={i === 0}
                           onFocus={() => setActive(i)}
                           onChange={(e) => { setRow(i, { amount: e.target.value }); setProposed(false) }} />
                  </div>
                  {!single && (
                    <button type="button" aria-label="Quitar pago" onClick={() => { setRows((rs) => rs.filter((_, j) => j !== i)); setActive(0) }}
                            className="h-12 w-12 rounded-xl text-ink-subtle hover:bg-surface-muted hover:text-danger flex items-center justify-center">
                      <X size={16} />
                    </button>
                  )}
                </div>
              )
            })}
            <button type="button" className="text-sm text-primary-ink hover:underline inline-flex items-center gap-1"
                    onClick={() => { setRows((rs) => [...rs, { methodId: (methods.find((m) => m.kind !== 'cash') ?? cashMethod).id,
                                                               amount: toInput(missing) }]); setActive(rows.length) }}>
              <Plus size={14} /> Pagar con varios medios
            </button>
          </div>

          {canDiscount && (
            <Input label="Descuento (opcional)" inputMode="numeric" placeholder="0" value={discount}
                   onChange={(e) => {
                     setDiscount(e.target.value)
                     // Con un solo pago, el valor a cobrar sigue al nuevo total
                     if (single) {
                       setRow(0, { amount: toInput(cartTotals(lines, parseAmount(e.target.value)).total) })
                       setProposed(true)
                     }
                   }} />
          )}

          <div className={cn('rounded-xl px-5 py-3 flex items-center justify-between',
            missing ? 'bg-warning-soft text-warning' : change ? 'bg-success-soft text-success' : 'bg-surface-muted text-ink-muted')}>
            <span className="text-sm font-medium">{missing ? 'Falta' : change ? 'Cambio a entregar' : 'Pago exacto'}</span>
            <span className="text-3xl font-semibold num">{formatCOP(fromCents(missing || change))}</span>
          </div>
          {invalidChange && <Alert tone="warning">Solo el efectivo puede superar el total para dar cambio.</Alert>}
          {pay.isError && <Alert tone="danger">{getErrorMessage(pay.error)}</Alert>}

          <Button type="submit" size="lg" fullWidth loading={pay.isPending} disabled={missing > 0 || invalidChange}
                  className="h-14 text-lg">
            Confirmar pago
          </Button>
        </div>

        {/* Derecha: billetes (efectivo) y teclado numérico en pantalla */}
        <div className="space-y-3 min-w-0">
          {cashSingle && (
            <div className="space-y-2">
              <p className="text-xs text-ink-muted">Billetes que te entregan (se suman)</p>
              <div className="grid grid-cols-4 gap-2">
                {CASH_BILLS.map((bill) => (
                  <button key={bill} type="button" onClick={() => tapBill(bill)} aria-label={`Sumar billete de ${formatCOP(bill)}`}
                          className="h-11 rounded-xl border border-line-strong bg-surface text-sm font-semibold text-ink hover:bg-surface-muted active:bg-primary-soft num">
                    {formatCOP(bill)}
                  </button>
                ))}
                <button type="button" onClick={setExact}
                        className="h-11 rounded-xl border border-primary bg-primary-soft text-sm font-semibold text-primary-ink hover:opacity-90">
                  Exacto
                </button>
              </div>
            </div>
          )}
          <div className="space-y-2">
            <p className="text-xs text-ink-muted">{cashSingle ? 'O escribe lo recibido con el teclado' : 'Escribe el valor con el teclado'}</p>
            <div role="group" aria-label="Teclado numérico" className="grid grid-cols-3 gap-2">
              {PAD.map((k) => (
                <button key={k.key} type="button" onClick={() => tapKey(k.key)} aria-label={k.aria}
                        className="h-12 rounded-xl border border-line-strong bg-surface text-xl font-semibold text-ink hover:bg-surface-muted active:bg-primary-soft num flex items-center justify-center">
                  {k.label}
                </button>
              ))}
            </div>
            <button type="button" onClick={() => tapKey('clear')} className="text-sm text-ink-muted hover:text-danger">
              Borrar lo recibido
            </button>
          </div>
        </div>
      </form>
    </Modal>
  )
}
