import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { billingApi } from '@/api/billing'
import { customersApi } from '@/api/customers'
import { catalogApi } from '@/api/catalog'
import Combobox, { type ComboOption } from '@/components/ui/Combobox'
import FormActions from '@/components/ui/FormActions'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import Textarea from '@/components/ui/Textarea'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP, toDisplayNumber } from '@/lib/money'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'
import type { InvoiceInput, Item } from '@/types'

interface Line {
  key: number
  product: (ComboOption & { product: Item }) | null
  quantity: string
  unitPrice: string
}

const today = () => new Date().toISOString().slice(0, 10)
const inDays = (days: number) => new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10)
let lineKey = 1

async function searchCustomers(term: string): Promise<ComboOption[]> {
  const res = await customersApi.list({ search: term || undefined, status: 'active', page_size: 20 })
  return res.results.map((c) => ({ id: c.id, label: c.company_name || c.full_name, description: c.document_number || c.email || undefined }))
}

async function searchProducts(term: string) {
  const res = await catalogApi.listItems({ search: term || undefined, is_active: true, is_sellable: true, page_size: 20 })
  return res.results.map((p) => ({ id: p.id, label: p.name, description: `${p.code} · ${formatCOP(p.price)}${p.unit === 'und' ? '' : ` / ${p.unit_symbol}`}`, product: p }))
}

/**
 * Nueva factura o cotización. La vista previa de totales es orientativa: el
 * backend recalcula todo (precio e IVA del catálogo, redondeo exacto) y es
 * el que decide si el usuario puede cambiar precios o aplicar descuentos.
 */
export default function InvoiceForm({ onSuccess, onCancel }: { onSuccess: () => void; onCancel?: () => void }) {
  const queryClient = useQueryClient()
  const can = useCan()
  const canOverridePrice = can('billing.override_price')
  const canDiscount = can('billing.apply_discount')

  const [number, setNumber] = useState('')
  const [invoiceType, setInvoiceType] = useState<'invoice' | 'quote'>('invoice')
  const [customer, setCustomer] = useState<ComboOption | null>(null)
  const [issueDate, setIssueDate] = useState(today())
  const [dueDate, setDueDate] = useState(inDays(30))
  const [discount, setDiscount] = useState('0')
  const [notes, setNotes] = useState('')
  const [lines, setLines] = useState<Line[]>([{ key: lineKey++, product: null, quantity: '1', unitPrice: '' }])
  const [errors, setErrors] = useState<Record<string, string>>({})

  const updateLine = (key: number, patch: Partial<Line>) =>
    setLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)))

  const preview = lines.map((l) => {
    const price = canOverridePrice && l.unitPrice !== '' ? Number(l.unitPrice) : toDisplayNumber(l.product?.product.price)
    const base = Number(l.quantity || 0) * price
    const rate = toDisplayNumber(l.product?.product.tax_rate)
    return { base, tax: (base * rate) / 100, rate }
  })
  const subtotal = preview.reduce((s, p) => s + p.base, 0)
  const tax = preview.reduce((s, p) => s + p.tax, 0)
  const total = subtotal + tax - (canDiscount ? Number(discount || 0) : 0)

  const mutation = useMutation({
    mutationFn: () => {
      const payload: InvoiceInput = {
        number: number.trim(), invoice_type: invoiceType, customer: customer!.id,
        issue_date: issueDate, due_date: dueDate, notes,
        ...(canDiscount ? { discount: discount || '0' } : {}),
        items: lines.map((l) => ({
          product: l.product!.id, quantity: l.quantity,
          ...(canOverridePrice && l.unitPrice !== '' ? { unit_price: l.unitPrice } : {}),
        })),
      }
      return billingApi.create(payload)
    },
    onSuccess: (inv) => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      queryClient.invalidateQueries({ queryKey: ['billing-summary'] })
      queryClient.invalidateQueries({ queryKey: ['recent-invoices'] })
      toast.success(`${inv.invoice_type === 'quote' ? 'Cotización' : 'Factura'} ${inv.number} creada por ${formatCOP(inv.total)}`)
      onSuccess()
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const next: Record<string, string> = {}
    if (!number.trim()) next.number = 'Indica el número del documento'
    if (!customer) next.customer = 'Selecciona un cliente'
    if (dueDate < issueDate) next.dueDate = 'No puede ser anterior a la emisión'
    if (lines.some((l) => !l.product)) next.lines = 'Selecciona el producto de cada línea'
    if (lines.some((l) => !(Number(l.quantity) > 0))) next.lines = 'Las cantidades deben ser mayores que 0'
    setErrors(next)
    if (Object.keys(next).length === 0) mutation.mutate()
  }

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <div className="grid sm:grid-cols-3 gap-4">
        <Input label="Número" required autoFocus placeholder="FAC-0001" value={number} onChange={(e) => setNumber(e.target.value)} error={errors.number} />
        <Select label="Tipo" value={invoiceType} onChange={(e) => setInvoiceType(e.target.value as 'invoice' | 'quote')}>
          <option value="invoice">Factura</option>
          <option value="quote">Cotización</option>
        </Select>
        <Combobox label="Cliente" required value={customer} onChange={setCustomer} search={searchCustomers}
                  queryKey="customers" placeholder="Buscar cliente…" error={errors.customer} />
        <Input label="Emisión" type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
        <Input label="Vencimiento" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} error={errors.dueDate} />
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-ink mb-2">Productos</legend>
        <div className="rounded-lg border border-line divide-y divide-line">
          {lines.map((line, index) => (
            <div key={line.key} className="grid grid-cols-[1fr_80px] sm:grid-cols-[1fr_90px_130px_110px_36px] gap-3 p-3 items-end">
              <Combobox label={index === 0 ? 'Producto' : undefined} value={line.product}
                        onChange={(opt) => updateLine(line.key, {
                          product: opt as Line['product'],
                          unitPrice: opt ? String(toDisplayNumber((opt as Line['product'])!.product.price)) : '',
                        })}
                        search={searchProducts} queryKey="products" placeholder="Buscar producto…" />
              <Input label={index === 0 ? 'Cant.' : undefined} aria-label="Cantidad" inputMode="decimal" value={line.quantity}
                     onChange={(e) => updateLine(line.key, { quantity: e.target.value })} />
              <Input label={index === 0 ? 'Precio unit.' : undefined} aria-label="Precio unitario" inputMode="decimal"
                     value={line.unitPrice} readOnly={!canOverridePrice}
                     title={canOverridePrice ? undefined : 'Precio del catálogo (no tienes permiso para cambiarlo)'}
                     onChange={(e) => updateLine(line.key, { unitPrice: e.target.value })} />
              <div className="text-right text-sm num pb-2 text-ink">
                {formatCOP(preview[index].base + preview[index].tax)}
                <span className="block text-[11px] text-ink-subtle">IVA {preview[index].rate} %</span>
              </div>
              <button type="button" onClick={() => setLines((prev) => prev.filter((l) => l.key !== line.key))}
                      disabled={lines.length === 1} aria-label={`Quitar línea ${index + 1}`}
                      className="h-9 w-9 flex items-center justify-center rounded-lg text-ink-subtle hover:text-danger hover:bg-danger-soft disabled:opacity-30 disabled:pointer-events-none">
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
        {errors.lines && <p className="text-xs text-danger">{errors.lines}</p>}
        <button type="button" onClick={() => setLines((prev) => [...prev, { key: lineKey++, product: null, quantity: '1', unitPrice: '' }])}
                className="inline-flex items-center gap-1 text-sm font-medium text-primary-ink hover:underline">
          <Plus size={14} /> Agregar línea
        </button>
      </fieldset>

      <div className="grid sm:grid-cols-2 gap-6">
        <Textarea label="Notas" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Condiciones de pago, observaciones…" />
        <dl className="text-sm space-y-2 self-end">
          <div className="flex justify-between text-ink-muted"><dt>Subtotal</dt><dd className="num">{formatCOP(subtotal)}</dd></div>
          <div className="flex justify-between text-ink-muted"><dt>Impuestos</dt><dd className="num">{formatCOP(tax)}</dd></div>
          <div className="flex justify-between items-center text-ink-muted gap-4">
            <dt>Descuento</dt>
            <dd className="w-32">
              <Input aria-label="Descuento" inputMode="decimal" value={discount} disabled={!canDiscount}
                     title={canDiscount ? undefined : 'No tienes permiso para aplicar descuentos'}
                     onChange={(e) => setDiscount(e.target.value)} className="text-right" />
            </dd>
          </div>
          <div className="flex justify-between pt-2 border-t border-line text-base font-semibold text-ink">
            <dt>Total estimado</dt><dd className="num">{formatCOP(total)}</dd>
          </div>
          <p className="text-[11px] text-ink-subtle text-right">El total definitivo lo calcula el sistema al guardar.</p>
        </dl>
      </div>

      <FormActions error={mutation.isError ? getErrorMessage(mutation.error) : null} submitting={mutation.isPending}
                   submitLabel={invoiceType === 'quote' ? 'Crear cotización' : 'Crear factura'} onCancel={onCancel} />
    </form>
  )
}
