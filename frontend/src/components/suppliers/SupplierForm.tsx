import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { suppliersApi } from '@/api/suppliers'
import FormActions from '@/components/ui/FormActions'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import Textarea from '@/components/ui/Textarea'
import { getErrorMessage } from '@/lib/errors'
import { PERSON_DOCUMENTS, SUPPLIER_CATEGORIES } from '@/lib/options'
import { toast } from '@/store/toastStore'
import type { Supplier } from '@/types'

const schema = z.object({
  company_name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  contact_name: z.string().optional(),
  document_type: z.enum(['NIT', 'CC', 'CE', 'PP']),
  document_number: z.string().optional(),
  email: z.union([z.literal(''), z.string().email('Email inválido')]),
  phone: z.string().optional(),
  city: z.string().optional(),
  website: z.union([z.literal(''), z.string().url('URL inválida (incluye https://)')]),
  category: z.enum(['materials', 'services', 'technology', 'logistics', 'marketing', 'other']),
  status: z.enum(['active', 'inactive']),
  notes: z.string().optional(),
})
type FormData = z.infer<typeof schema>

export default function SupplierForm({ supplier, onSuccess, onCancel }: {
  supplier?: Supplier; onSuccess: () => void; onCancel?: () => void
}) {
  const queryClient = useQueryClient()
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      company_name: supplier?.company_name ?? '', contact_name: supplier?.contact_name ?? '',
      document_type: supplier?.document_type ?? 'NIT', document_number: supplier?.document_number ?? '',
      email: supplier?.email ?? '', phone: supplier?.phone ?? '', city: supplier?.city ?? '',
      website: supplier?.website ?? '', category: supplier?.category ?? 'materials',
      status: supplier?.status ?? 'active', notes: supplier?.notes ?? '',
    },
  })
  const mutation = useMutation({
    mutationFn: (data: FormData) => (supplier ? suppliersApi.update(supplier.id, data) : suppliersApi.create(data)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] })
      toast.success(supplier ? 'Proveedor actualizado' : 'Proveedor creado')
      onSuccess()
    },
  })

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4" noValidate>
      <Input label="Razón social o nombre" required autoFocus {...register('company_name')} error={errors.company_name?.message} />
      <div className="grid sm:grid-cols-[180px_1fr] gap-4">
        <Select label="Documento" {...register('document_type')}>
          {PERSON_DOCUMENTS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
        </Select>
        <Input label="Número de documento" {...register('document_number')} />
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <Input label="Persona de contacto" {...register('contact_name')} />
        <Select label="Categoría" {...register('category')}>
          {SUPPLIER_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </Select>
        <Input label="Email" type="email" {...register('email')} error={errors.email?.message} />
        <Input label="Teléfono" type="tel" {...register('phone')} />
        <Input label="Ciudad" {...register('city')} />
        <Select label="Estado" {...register('status')}>
          <option value="active">Activo</option>
          <option value="inactive">Inactivo</option>
        </Select>
      </div>
      <Input label="Sitio web" placeholder="https://" {...register('website')} error={errors.website?.message} />
      <Textarea label="Notas" rows={2} {...register('notes')} />
      <FormActions error={mutation.isError ? getErrorMessage(mutation.error) : null} submitting={mutation.isPending}
                   submitLabel={supplier ? 'Guardar cambios' : 'Crear proveedor'} onCancel={onCancel} />
    </form>
  )
}
