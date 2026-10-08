import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { billingApi } from '@/api/billing'
import { customersApi } from '@/api/customers'
import { inventoryApi } from '@/api/inventory'
import Input from '@/components/ui/Input'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { useCan } from '@/store/authStore'
import type { InvoiceInput } from '@/types'

// ── Validación ────────────────────────────────────
const itemSchema = z.object({
  product:    z.coerce.number().min(1, 'Selecciona un producto'),
  quantity:   z.coerce.number().min(0.01, 'Mínimo 0.01'),
  // Solo se envía si el usuario tiene permiso de cambiar precios; si no, el backend usa el del catálogo
  unit_price: z.coerce.number().min(0, 'Precio inválido').optional(),
  description: z.string().optional(),
})

const invoiceSchema = z.object({
  number:       z.string().min(1, 'El número es obligatorio'),
  invoice_type: z.enum(['invoice', 'quote']),
  status:       z.enum(['draft', 'sent', 'paid', 'overdue', 'cancelled']),
  customer:     z.coerce.number().min(1, 'Selecciona un cliente'),
  issue_date:   z.string().min(1, 'La fecha es obligatoria'),
  due_date:     z.string().min(1, 'La fecha de vencimiento es obligatoria'),
  discount:     z.coerce.number().min(0).default(0),
  notes:        z.string().optional(),
  items:        z.array(itemSchema).min(1, 'Agrega al menos un producto'),
})

type InvoiceFormData = z.infer<typeof invoiceSchema>

interface InvoiceFormProps {
  onSuccess: () => void
}

export default function InvoiceForm({ onSuccess }: InvoiceFormProps) {
  const queryClient = useQueryClient()
  const can = useCan()
  const canOverridePrice = can('billing.override_price')
  const canDiscount = can('billing.apply_discount')

  // TODO(fase 5): reemplazar estos <select> por un combobox con búsqueda en servidor.
  const { data: clientsData } = useQuery({
    queryKey: ['customers-select'],
    queryFn: () => customersApi.list({ status: 'active', page_size: 100 }),
  })

  const { data: productsData } = useQuery({
    queryKey: ['products-select'],
    queryFn: () => inventoryApi.listProducts({ is_active: true, page_size: 100 }),
  })

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
    control,
  } = useForm<InvoiceFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(invoiceSchema) as any,
    defaultValues: {
      invoice_type: 'invoice',
      status:       'draft',
      discount:     0,
      items:        [{ product: 0, quantity: 1, unit_price: 0, description: '' }],
    },
  })

  // useFieldArray maneja el array dinámico de líneas
  const { fields, append, remove } = useFieldArray({ control, name: 'items' })

  const mutation = useMutation({
    mutationFn: billingApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      queryClient.invalidateQueries({ queryKey: ['billing-summary'] })
      onSuccess()
    },
  })

  const productById = (id: number) => productsData?.results.find(p => p.id === id)

  // Cuando el usuario selecciona un producto, muestra el precio del catálogo
  const handleProductChange = (index: number, productId: number) => {
    const product = productById(productId)
    if (product) setValue(`items.${index}.unit_price`, Number(product.price))
  }

  // Vista previa en vivo. El importe definitivo (con redondeo exacto) lo calcula el servidor.
  const watchItems    = watch('items') ?? []
  const watchDiscount = watch('discount') ?? 0
  const previewLine = (item: InvoiceFormData['items'][number] | undefined) => {
    const product = item ? productById(Number(item.product)) : undefined
    const price = canOverridePrice ? Number(item?.unit_price ?? 0) : Number(product?.price ?? 0)
    const base = Number(item?.quantity ?? 0) * price
    return { base, tax: base * Number(product?.tax_rate ?? 0) / 100, taxRate: product?.tax_rate }
  }
  const subtotal  = watchItems.reduce((sum, item) => sum + previewLine(item).base, 0)
  const taxAmount = watchItems.reduce((sum, item) => sum + previewLine(item).tax, 0)
  const total = subtotal + taxAmount - Number(watchDiscount)

  const onSubmit = (data: InvoiceFormData) => {
    const payload: InvoiceInput = {
      number: data.number, invoice_type: data.invoice_type, status: data.status,
      customer: data.customer, issue_date: data.issue_date, due_date: data.due_date,
      notes: data.notes ?? '',
      ...(canDiscount ? { discount: data.discount } : {}),
      items: data.items.map((item) => ({
        product: item.product,
        quantity: item.quantity,
        description: item.description,
        ...(canOverridePrice ? { unit_price: item.unit_price } : {}),
      })),
    }
    mutation.mutate(payload)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {/* Cabecera */}
      <div className="grid grid-cols-3 gap-3">
        <Input
          label="Número"
          {...register('number')}
          error={errors.number?.message}
          placeholder="FAC-2026-002"
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
          <select
            {...register('invoice_type')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="invoice">Factura</option>
            <option value="quote">Cotización</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
          <select
            {...register('status')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="draft">Borrador</option>
            <option value="sent">Enviada</option>
            <option value="paid">Pagada</option>
          </select>
        </div>
      </div>

      {/* Cliente y fechas */}
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">Cliente</label>
          <select
            {...register('customer')}
            className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
              errors.customer ? 'border-red-400' : 'border-gray-300'
            }`}
          >
            <option value={0}>Seleccionar...</option>
            {clientsData?.results.map(c => (
              <option key={c.id} value={c.id}>{c.full_name}</option>
            ))}
          </select>
          {errors.customer && <p className="mt-1 text-xs text-red-600">{errors.customer.message}</p>}
        </div>
        <Input
          label="Fecha emisión"
          type="date"
          {...register('issue_date')}
          error={errors.issue_date?.message}
        />
        <Input
          label="Fecha vencimiento"
          type="date"
          {...register('due_date')}
          error={errors.due_date?.message}
        />
      </div>

      {/* Líneas de productos */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">Productos / Servicios</label>
          <button
            type="button"
            onClick={() => append({ product: 0, quantity: 1, unit_price: 0, description: '' })}
            className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-medium"
          >
            <Plus size={13} /> Agregar línea
          </button>
        </div>

        {errors.items?.root && (
          <p className="text-xs text-red-600 mb-2">{errors.items.root.message}</p>
        )}

        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-2">Producto</th>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-2 w-20">Cant.</th>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-2 w-28">Precio unit.</th>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-2 w-16">IVA %</th>
                <th className="text-left text-xs text-gray-500 font-medium px-3 py-2 w-28">Subtotal</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {fields.map((field, index) => {
                const preview = previewLine(watchItems[index])
                const lineTotal = preview.base + preview.tax

                return (
                  <tr key={field.id}>
                    <td className="px-3 py-2">
                      <select
                        {...register(`items.${index}.product`, {
                          onChange: (e) => handleProductChange(index, Number(e.target.value))
                        })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      >
                        <option value={0}>Seleccionar...</option>
                        {productsData?.results.map(p => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        step="0.01"
                        {...register(`items.${index}.quantity`)}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        step="0.01"
                        readOnly={!canOverridePrice}
                        title={canOverridePrice ? undefined : 'Precio del catálogo (no tienes permiso para cambiarlo)'}
                        {...register(`items.${index}.unit_price`)}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 read-only:bg-gray-50 read-only:text-gray-500"
                      />
                    </td>
                    <td className="px-3 py-2 text-gray-500 tabular-nums">
                      {preview.taxRate != null ? `${Number(preview.taxRate)} %` : '—'}
                    </td>
                    <td className="px-3 py-2 text-gray-900 font-medium whitespace-nowrap">
                      {formatCOP(lineTotal)}
                    </td>
                    <td className="px-3 py-2">
                      {fields.length > 1 && (
                        <button
                          type="button"
                          onClick={() => remove(index)}
                          className="text-gray-400 hover:text-red-500 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Totales y descuento */}
      <div className="flex justify-end">
        <div className="w-64 space-y-2 text-sm">
          <div className="flex justify-between text-gray-600">
            <span>Subtotal</span>
            <span>{formatCOP(subtotal)}</span>
          </div>
          <div className="flex justify-between text-gray-600">
            <span>IVA</span>
            <span>{formatCOP(taxAmount)}</span>
          </div>
          <div className="flex justify-between items-center text-gray-600">
            <span>Descuento</span>
            <input
              type="number"
              step="0.01"
              disabled={!canDiscount}
              title={canDiscount ? undefined : 'No tienes permiso para aplicar descuentos'}
              {...register('discount')}
              className="w-28 disabled:bg-gray-50 disabled:text-gray-400 border border-gray-300 rounded px-2 py-1 text-sm text-right focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="flex justify-between font-bold text-gray-900 text-base pt-2 border-t border-gray-200">
            <span>Total estimado</span>
            <span>{formatCOP(total)}</span>
          </div>
        </div>
      </div>

      {/* Notas */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Notas (opcional)</label>
        <textarea
          {...register('notes')}
          rows={2}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          placeholder="Condiciones de pago, observaciones..."
        />
      </div>

      {mutation.isError && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          {getErrorMessage(mutation.error)}
        </p>
      )}

      <div className="flex justify-end pt-2">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          {mutation.isPending ? 'Guardando...' : 'Crear factura'}
        </button>
      </div>
    </form>
  )
}
