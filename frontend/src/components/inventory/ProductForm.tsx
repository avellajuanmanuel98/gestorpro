import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { inventoryApi } from '@/api/inventory'
import FormActions from '@/components/ui/FormActions'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import Textarea from '@/components/ui/Textarea'
import { getErrorMessage } from '@/lib/errors'
import { toast } from '@/store/toastStore'
import type { Product } from '@/types'

const money = z.string().trim().regex(/^\d+(\.\d{1,2})?$/, 'Usa solo números (ej. 1800 o 1800.50)')
const schema = z.object({
  name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  code: z.string().trim().min(1, 'Indica un código'),
  description: z.string().optional(),
  product_type: z.enum(['product', 'service']),
  category: z.string(),
  price: money,
  tax_rate: z.string(),
  stock: z.coerce.number().int('Solo unidades enteras').min(0, 'No puede ser negativo'),
  minimum_stock: z.coerce.number().int('Solo unidades enteras').min(0, 'No puede ser negativo'),
  is_active: z.enum(['true', 'false']),
})
type FormInput = z.input<typeof schema>
type FormData = z.output<typeof schema>

// Tarifas habituales en Colombia. El backend valida el rango (0–100).
const TAX_RATES = ['0', '5', '8', '19']

export default function ProductForm({ product, onSuccess, onCancel }: {
  product?: Product; onSuccess: () => void; onCancel?: () => void
}) {
  const queryClient = useQueryClient()
  const categories = useQuery({ queryKey: ['categories', 'select'], queryFn: () => inventoryApi.listCategories({ page_size: 100 }) })
  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormInput, unknown, FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: product?.name ?? '', code: product?.code ?? '', description: product?.description ?? '',
      product_type: product?.product_type ?? 'product', category: product?.category ? String(product.category) : '',
      price: product ? String(Number(product.price)) : '', tax_rate: product ? String(Number(product.tax_rate)) : '19',
      stock: product?.stock ?? 0, minimum_stock: product?.minimum_stock ?? 5,
      is_active: product?.is_active === false ? 'false' : 'true',
    },
  })
  const isService = watch('product_type') === 'service'

  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      const payload = { ...data, category: data.category ? Number(data.category) : null, is_active: data.is_active === 'true' }
      return product ? inventoryApi.updateProduct(product.id, payload) : inventoryApi.createProduct(payload)
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['low-stock'] })
      toast.success(product ? `«${saved.name}» actualizado` : `«${saved.name}» agregado al catálogo`)
      onSuccess()
    },
  })

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4" noValidate>
      <div className="grid sm:grid-cols-[1fr_160px] gap-4">
        <Input label="Nombre" required autoFocus {...register('name')} error={errors.name?.message} />
        <Input label="Código" required placeholder="PAN-001" {...register('code')} error={errors.code?.message} />
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <Select label="Categoría" {...register('category')}>
          <option value="">Sin categoría</option>
          {categories.data?.results.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>
        <Select label="Tipo" {...register('product_type')}>
          <option value="product">Producto (maneja stock)</option>
          <option value="service">Servicio</option>
        </Select>
        <Input label="Precio de venta (COP)" required inputMode="decimal" {...register('price')} error={errors.price?.message}
               hint="Sin IVA. El total con impuestos lo calcula el sistema." />
        <Select label="IVA / impuesto" {...register('tax_rate')}>
          {TAX_RATES.map((r) => <option key={r} value={r}>{r} %</option>)}
        </Select>
        {!isService && (
          <>
            <Input label="Stock actual" type="number" min={0} {...register('stock')} error={errors.stock?.message}
                   hint="Se reemplazará por movimientos de inventario en la fase de inventario." />
            <Input label="Stock mínimo" type="number" min={0} {...register('minimum_stock')} error={errors.minimum_stock?.message}
                   hint="Por debajo de este número verás una alerta." />
          </>
        )}
      </div>
      <Textarea label="Descripción" rows={2} {...register('description')} />
      <Select label="Estado" {...register('is_active')}>
        <option value="true">Activo (disponible para vender)</option>
        <option value="false">Inactivo</option>
      </Select>
      <FormActions error={mutation.isError ? getErrorMessage(mutation.error) : null} submitting={mutation.isPending}
                   submitLabel={product ? 'Guardar cambios' : 'Crear producto'} onCancel={onCancel} />
    </form>
  )
}
