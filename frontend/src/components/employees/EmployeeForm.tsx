import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { employeesApi } from '@/api/employees'
import type { Employee } from '@/types'
import Input from '@/components/ui/Input'

const DEPARTMENTS = [
  { value: 'admin',      label: 'Administración' },
  { value: 'sales',      label: 'Ventas' },
  { value: 'operations', label: 'Operaciones' },
  { value: 'finance',    label: 'Finanzas' },
  { value: 'it',         label: 'Tecnología' },
  { value: 'hr',         label: 'Recursos Humanos' },
  { value: 'other',      label: 'Otro' },
] as const

const employeeSchema = z.object({
  document_type:   z.enum(['CC', 'CE', 'PP']),
  document_number: z.string().min(5, 'Mínimo 5 caracteres'),
  first_name:      z.string().min(2, 'Mínimo 2 caracteres'),
  last_name:       z.string().min(2, 'Mínimo 2 caracteres'),
  email:           z.string().email('Email inválido'),
  phone:           z.string().optional(),
  city:            z.string().optional(),
  position:        z.string().min(2, 'Mínimo 2 caracteres'),
  department:      z.enum(['admin', 'sales', 'operations', 'finance', 'it', 'hr', 'other']),
  hire_date:       z.string().min(1, 'Requerido'),
  salary:          z.string().optional(),
  status:          z.enum(['active', 'inactive']),
  notes:           z.string().optional(),
})

type EmployeeFormData = z.infer<typeof employeeSchema>

interface EmployeeFormProps {
  employee?: Employee
  onSuccess: () => void
}

export default function EmployeeForm({ employee, onSuccess }: EmployeeFormProps) {
  const queryClient = useQueryClient()
  const isEditing   = !!employee

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EmployeeFormData>({
    resolver: zodResolver(employeeSchema),
    defaultValues: {
      document_type:   employee?.document_type   ?? 'CC',
      document_number: employee?.document_number ?? '',
      first_name:      employee?.first_name      ?? '',
      last_name:       employee?.last_name        ?? '',
      email:           employee?.email            ?? '',
      phone:           employee?.phone            ?? '',
      city:            employee?.city             ?? '',
      position:        employee?.position         ?? '',
      department:      employee?.department       ?? 'other',
      hire_date:       employee?.hire_date        ?? '',
      salary:          employee?.salary           ?? '',
      status:          employee?.status           ?? 'active',
      notes:           employee?.notes            ?? '',
    },
  })

  const mutation = useMutation({
    mutationFn: (data: EmployeeFormData) =>
      isEditing
        ? employeesApi.update(employee!.id, data)
        : employeesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] })
      onSuccess()
    },
  })

  const onSubmit = (data: EmployeeFormData) => mutation.mutate(data)

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Documento */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo doc.</label>
          <select
            {...register('document_type')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="CC">CC</option>
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

      {/* Nombre */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Nombre"
          {...register('first_name')}
          error={errors.first_name?.message}
          placeholder="María"
        />
        <Input
          label="Apellido"
          {...register('last_name')}
          error={errors.last_name?.message}
          placeholder="González"
        />
      </div>

      {/* Email y teléfono */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Email"
          type="email"
          {...register('email')}
          error={errors.email?.message}
          placeholder="maria@empresa.com"
        />
        <Input
          label="Teléfono"
          {...register('phone')}
          placeholder="3001234567"
        />
      </div>

      {/* Cargo y departamento */}
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Cargo"
          {...register('position')}
          error={errors.position?.message}
          placeholder="Analista de ventas"
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Departamento</label>
          <select
            {...register('department')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {DEPARTMENTS.map(d => (
              <option key={d.value} value={d.value}>{d.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Fecha de contratación y salario */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Fecha de contratación</label>
          <input
            type="date"
            {...register('hire_date')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          {errors.hire_date && (
            <p className="text-xs text-red-600 mt-1">{errors.hire_date.message}</p>
          )}
        </div>
        <Input
          label="Salario (opcional)"
          type="number"
          {...register('salary')}
          placeholder="2500000"
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
          placeholder="Información adicional del empleado..."
        />
      </div>

      {mutation.isError && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          Ocurrió un error. Verifica que el email y documento no estén duplicados.
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
            : isEditing ? 'Guardar cambios' : 'Crear empleado'}
        </button>
      </div>
    </form>
  )
}
