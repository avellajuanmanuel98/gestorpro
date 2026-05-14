import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { inventoryApi } from '@/api/inventory'
import type { Product } from '@/types'
import Input from '@/components/ui/Input'

const productSchema = z.object({
  name:          z.string().min(2, 'Mínimo 2 caracteres'),
  code:          z.string().min(1, 'Requerido'),
  description:   z.string().optional(),
  product_type:  z.enum(['product', 'service']),
  category:      z.number().nullable().optional(),
  price:         z.string().min(1, 'Requerido'),
  tax_rate:      z.string(),
  stock:         z.number().min(0).optional(),
  minimum_stock: z.number().min(0).optional(),
  is_active:     z.boolean(),
})

type ProductFormData = z.infer<typeof productSchema>

interface ProductFormProps {
  product?: Product
  onSuccess: () => void
}

export default function ProductForm({ product, onSuccess }: ProductFormProps) {
  const queryClient = useQueryClient()
  const isEditing   = !!product

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn:  inventoryApi.listCategories,
  })

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ProductFormData>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      name:          product?.name          ?? '',
      code:          product?.code          ?? '',
      description:   product?.description   ?? '',
      product_type:  product?.product_type  ?? 'product',
      category:      product?.category      ?? null,
      price:         product?.price         ?? '',
      tax_rate:      product?.tax_rate      ?? '19.00',
      stock:         product?.stock         ?? 0,
      minimum_stock: product?.minimum_stock ?? 5,
      is_active:     product?.is_active     ?? true,
    },
  })

  const productType = watch('product_type')

  const mutation = useMutation({
    mutationFn: (data: ProductFormData) => {
      const payload = {
        ...data,
        category: data.category || null,
        stock:    productType === 'service' ? 0 : data.stock,
      }
      return isEditing
        ? inventoryApi.updateProduct(product!.id, payload)
        : inventoryApi.createProduct(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      onSuccess()
    },
  })

  const onSubmit = (data: ProductFormData) => mutation.mutate(data)

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Nombre y código */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Nombre"
          {...register('name')}
          error={errors.name?.message}
          placeholder="Camiseta básica"
        />
        <Input
          label="Código / SKU"
          {...register('code')}
          error={errors.code?.message}
          placeholder="CAM-001"
        />
      </div>

      {/* Tipo y categoría */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
          <select
            {...register('product_type')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="product">Producto físico</option>
            <option value="service">Servicio</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Categoría (opcional)</label>
          <select
            {...register('category', { setValueAs: v => v === '' ? null : Number(v) })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Sin categoría</option>
            {categories?.results.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Descripción */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Descripción (opcional)</label>
        <textarea
          {...register('description')}
          rows={2}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          placeholder="Descripción del producto..."
        />
      </div>

      {/* Precio e IVA */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Precio (sin IVA)"
          type="number"
          step="0.01"
          {...register('price')}
          error={errors.price?.message}
          placeholder="50000"
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">IVA (%)</label>
          <select
            {...register('tax_rate')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="0.00">0% — Exento</option>
            <option value="5.00">5%</option>
            <option value="19.00">19% — General</option>
          </select>
        </div>
      </div>

      {/* Stock (solo para productos físicos) */}
      {productType === 'product' && (
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Stock actual"
            type="number"
            {...register('stock', { valueAsNumber: true })}
            placeholder="0"
          />
          <Input
            label="Stock mínimo"
            type="number"
            {...register('minimum_stock', { valueAsNumber: true })}
            placeholder="5"
          />
        </div>
      )}

      {/* Estado */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_active"
          {...register('is_active')}
          className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
        />
        <label htmlFor="is_active" className="text-sm text-gray-700">Producto activo</label>
      </div>

      {mutation.isError && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          Error al guardar. Verifica que el código no esté duplicado.
        </p>
      )}

      <div className="flex justify-end pt-2">
        <button
          type="submit"
          disabled={isSubmitting || mutation.isPending}
          className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          {mutation.isPending ? 'Guardando...' : isEditing ? 'Guardar cambios' : 'Crear producto'}
        </button>
      </div>
    </form>
  )
}
