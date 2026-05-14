import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { suppliersApi } from '@/api/suppliers'
import type { Supplier } from '@/types'
import Input from '@/components/ui/Input'

const CATEGORIES = [
  { value: 'materials',  label: 'Materiales e insumos' },
  { value: 'services',   label: 'Servicios' },
  { value: 'technology', label: 'Tecnología' },
  { value: 'logistics',  label: 'Logística y transporte' },
  { value: 'marketing',  label: 'Marketing y publicidad' },
  { value: 'other',      label: 'Otro' },
] as const

const supplierSchema = z.object({
  company_name:    z.string().min(2, 'Mínimo 2 caracteres'),
  contact_name:    z.string().optional(),
  document_type:   z.enum(['NIT', 'CC', 'CE', 'PP']),
  document_number: z.string().optional(),
  email:           z.string().email('Email inválido').or(z.literal('')).optional(),
  phone:           z.string().optional(),
  city:            z.string().optional(),
  website:         z.string().url('URL inválida').or(z.literal('')).optional(),
  category:        z.enum(['materials', 'services', 'technology', 'logistics', 'marketing', 'other']),
  status:          z.enum(['active', 'inactive']),
  notes:           z.string().optional(),
})

type SupplierFormData = z.infer<typeof supplierSchema>

interface SupplierFormProps {
  supplier?: Supplier
  onSuccess: () => void
}

export default function SupplierForm({ supplier, onSuccess }: SupplierFormProps) {
  const queryClient = useQueryClient()
  const isEditing   = !!supplier

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SupplierFormData>({
    resolver: zodResolver(supplierSchema),
    defaultValues: {
      company_name:    supplier?.company_name    ?? '',
      contact_name:    supplier?.contact_name    ?? '',
      document_type:   supplier?.document_type   ?? 'NIT',
      document_number: supplier?.document_number ?? '',
      email:           supplier?.email           ?? '',
      phone:           supplier?.phone           ?? '',
      city:            supplier?.city            ?? '',
      website:         supplier?.website         ?? '',
      category:        supplier?.category        ?? 'other',
      status:          supplier?.status          ?? 'active',
      notes:           supplier?.notes           ?? '',
    },
  })

  const mutation = useMutation({
    mutationFn: (data: SupplierFormData) =>
      isEditing
        ? suppliersApi.update(supplier!.id, data)
        : suppliersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] })
      onSuccess()
    },
  })

  const onSubmit = (data: SupplierFormData) => mutation.mutate(data)

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Nombre empresa */}
      <Input
        label="Nombre de la empresa"
        {...register('company_name')}
        error={errors.company_name?.message}
        placeholder="Distribuidora Nacional S.A.S"
      />

      {/* Contacto */}
      <Input
        label="Nombre del contacto (opcional)"
        {...register('contact_name')}
        placeholder="Juan Pérez"
      />

      {/* Documento */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo doc.</label>
          <select
            {...register('document_type')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="NIT">NIT</option>
            <option value="CC">CC</option>
            <option value="CE">CE</option>
            <option value="PP">Pasaporte</option>
          </select>
        </div>
        <div className="col-span-2">
          <Input
            label="Número de documento (opcional)"
            {...register('document_number')}
            placeholder="900123456-1"
          />
        </div>
      </div>

      {/* Email y teléfono */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Email (opcional)"
          type="email"
          {...register('email')}
          error={errors.email?.message}
          placeholder="ventas@proveedor.com"
        />
        <Input
          label="Teléfono (opcional)"
          {...register('phone')}
          placeholder="6011234567"
        />
      </div>

      {/* Ciudad y categoría */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Ciudad (opcional)"
          {...register('city')}
          placeholder="Medellín"
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
          <select
            {...register('category')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {CATEGORIES.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Sitio web y estado */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Sitio web (opcional)"
          {...register('website')}
          error={errors.website?.message}
          placeholder="https://proveedor.com"
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
          <select
            {...register('status')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="active">Activo</option>
            <option value="inactive">Inactivo</option>
          </select>
        </div>
      </div>

      {/* Notas */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Notas (opcional)</label>
        <textarea
          {...register('notes')}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          placeholder="Condiciones de pago, tiempos de entrega..."
        />
      </div>

      {mutation.isError && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          Ocurrió un error al guardar. Intenta de nuevo.
        </p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="submit"
          disabled={isSubmitting || mutation.isPending}
          className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          {mutation.isPending
            ? 'Guardando...'
            : isEditing ? 'Guardar cambios' : 'Crear proveedor'}
        </button>
      </div>
    </form>
  )
}
