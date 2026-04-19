import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { clientsApi } from '@/api/clients'
import type { Client } from '@/types'
import Input from '@/components/ui/Input'

// ── Esquema de validación con Zod ─────────────────
// Zod valida los datos ANTES de enviarlos al backend
const clientSchema = z.object({
  document_type:   z.enum(['CC', 'NIT', 'CE', 'PP']),
  document_number: z.string().min(5, 'Mínimo 5 caracteres'),
  first_name:      z.string().min(2, 'Mínimo 2 caracteres'),
  last_name:       z.string().min(2, 'Mínimo 2 caracteres'),
  company_name:    z.string().optional(),
  email:           z.string().email('Email inválido'),
  phone:           z.string().optional(),
  city:            z.string().optional(),
  status:          z.enum(['active', 'inactive']),
  notes:           z.string().optional(),
})

type ClientFormData = z.infer<typeof clientSchema>

interface ClientFormProps {
  client?: Client       // Si viene un cliente, es edición. Si no, es creación.
  onSuccess: () => void // Se llama cuando el formulario se guarda exitosamente
}

export default function ClientForm({ client, onSuccess }: ClientFormProps) {
  const queryClient = useQueryClient()
  const isEditing   = !!client

  const {
    register,           // conecta cada input con react-hook-form
    handleSubmit,       // envuelve el onSubmit con validación automática
    formState: { errors, isSubmitting },
  } = useForm<ClientFormData>({
    resolver: zodResolver(clientSchema),
    defaultValues: {
      document_type:   client?.document_type   ?? 'CC',
      document_number: client?.document_number ?? '',
      first_name:      client?.first_name      ?? '',
      last_name:       client?.last_name       ?? '',
      company_name:    client?.company_name    ?? '',
      email:           client?.email           ?? '',
      phone:           client?.phone           ?? '',
      city:            client?.city            ?? '',
      status:          client?.status          ?? 'active',
      notes:           client?.notes           ?? '',
    },
  })

  // useMutation maneja el estado de la petición (loading, error, success)
  const mutation = useMutation({
    mutationFn: (data: ClientFormData) =>
      isEditing
        ? clientsApi.update(client!.id, data)
        : clientsApi.create(data),
    onSuccess: () => {
      // Invalida el caché de clientes → React Query hace el fetch automáticamente
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      onSuccess()
    },
  })

  const onSubmit = (data: ClientFormData) => mutation.mutate(data)

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Tipo y número de documento */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo doc.</label>
          <select
            {...register('document_type')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="CC">CC</option>
            <option value="NIT">NIT</option>
            <option value="CE">CE</option>
            <option value="PP">Pasaporte</option>
          </select>
        </div>
        <div className="col-span-2">
          <Input
            label="Número de documento"
            {...register('document_number')}
            error={errors.document_number?.message}
            placeholder="1234567890"
          />
        </div>
      </div>

      {/* Nombre y apellido */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Nombre"
          {...register('first_name')}
          error={errors.first_name?.message}
          placeholder="Carlos"
        />
        <Input
          label="Apellido"
          {...register('last_name')}
          error={errors.last_name?.message}
          placeholder="Ramírez"
        />
      </div>

      {/* Empresa */}
      <Input
        label="Empresa (opcional)"
        {...register('company_name')}
        placeholder="Ferretería El Tornillo"
      />

      {/* Email y teléfono */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Email"
          type="email"
          {...register('email')}
          error={errors.email?.message}
          placeholder="carlos@empresa.com"
        />
        <Input
          label="Teléfono"
          {...register('phone')}
          placeholder="3001234567"
        />
      </div>

      {/* Ciudad y estado */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Ciudad"
          {...register('city')}
          placeholder="Bogotá"
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
          placeholder="Información adicional del cliente..."
        />
      </div>

      {/* Error general */}
      {mutation.isError && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          Ocurrió un error. Verifica que el email y documento no estén duplicados.
        </p>
      )}

      {/* Botones */}
      <div className="flex justify-end gap-3 pt-2">
        <button
          type="submit"
          disabled={isSubmitting || mutation.isPending}
          className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          {mutation.isPending
            ? 'Guardando...'
            : isEditing ? 'Guardar cambios' : 'Crear cliente'}
        </button>
      </div>
    </form>
  )
}
