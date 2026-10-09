import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { customersApi } from '@/api/customers'
import FormActions from '@/components/ui/FormActions'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import Textarea from '@/components/ui/Textarea'
import { getErrorMessage } from '@/lib/errors'
import { PERSON_DOCUMENTS } from '@/lib/options'
import { toast } from '@/store/toastStore'
import type { Customer } from '@/types'

const schema = z.object({
  first_name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  last_name: z.string().optional(),
  company_name: z.string().optional(),
  document_type: z.enum(['CC', 'NIT', 'CE', 'PP']),
  document_number: z.string().optional(),
  email: z.union([z.literal(''), z.string().email('Email inválido')]),
  phone: z.string().optional(),
  city: z.string().optional(),
  address: z.string().optional(),
  status: z.enum(['active', 'inactive']),
  notes: z.string().optional(),
})
type FormData = z.infer<typeof schema>

export default function ClientForm({ client, onSuccess, onCancel }: {
  client?: Customer; onSuccess: () => void; onCancel?: () => void
}) {
  const queryClient = useQueryClient()
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: client?.first_name ?? '', last_name: client?.last_name ?? '', company_name: client?.company_name ?? '',
      document_type: client?.document_type ?? 'CC', document_number: client?.document_number ?? '',
      email: client?.email ?? '', phone: client?.phone ?? '', city: client?.city ?? '', address: client?.address ?? '',
      status: client?.status ?? 'active', notes: client?.notes ?? '',
    },
  })
  const mutation = useMutation({
    mutationFn: (data: FormData) => (client ? customersApi.update(client.id, data) : customersApi.create(data)),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      toast.success(client ? 'Cliente actualizado' : `Cliente «${saved.full_name}» creado`)
      onSuccess()
    },
  })

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4" noValidate>
      <div className="grid sm:grid-cols-2 gap-4">
        <Input label="Nombre" required autoFocus {...register('first_name')} error={errors.first_name?.message} />
        <Input label="Apellido" {...register('last_name')} />
      </div>
      <Input label="Razón social" hint="Solo si el cliente es una empresa" {...register('company_name')} />
      <div className="grid sm:grid-cols-[180px_1fr] gap-4">
        <Select label="Documento" {...register('document_type')}>
          {PERSON_DOCUMENTS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
        </Select>
        <Input label="Número de documento" hint="Opcional para consumidor final" {...register('document_number')} />
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <Input label="Email" type="email" {...register('email')} error={errors.email?.message} />
        <Input label="Teléfono" type="tel" {...register('phone')} />
        <Input label="Ciudad" {...register('city')} />
        <Select label="Estado" {...register('status')}>
          <option value="active">Activo</option>
          <option value="inactive">Inactivo</option>
        </Select>
      </div>
      <Input label="Dirección" {...register('address')} />
      <Textarea label="Notas" rows={2} {...register('notes')} />
      <FormActions error={mutation.isError ? getErrorMessage(mutation.error) : null} submitting={mutation.isPending}
                   submitLabel={client ? 'Guardar cambios' : 'Crear cliente'} onCancel={onCancel} />
    </form>
  )
}
