import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { employeesApi } from '@/api/employees'
import FormActions from '@/components/ui/FormActions'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import Textarea from '@/components/ui/Textarea'
import { getErrorMessage } from '@/lib/errors'
import { DEPARTMENTS } from '@/lib/options'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'
import type { Employee } from '@/types'

const schema = z.object({
  first_name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  last_name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  document_type: z.enum(['CC', 'CE', 'PP']),
  document_number: z.string().trim().min(5, 'Mínimo 5 caracteres'),
  email: z.union([z.literal(''), z.string().email('Email inválido')]),
  phone: z.string().optional(),
  city: z.string().optional(),
  position: z.string().trim().min(2, 'Indica el cargo'),
  department: z.enum(['admin', 'sales', 'operations', 'finance', 'it', 'hr', 'other']),
  hire_date: z.string().min(1, 'Indica la fecha de ingreso'),
  salary: z.string().optional(),
  status: z.enum(['active', 'inactive']),
  notes: z.string().optional(),
})
type FormData = z.infer<typeof schema>

export default function EmployeeForm({ employee, onSuccess, onCancel }: {
  employee?: Employee; onSuccess: () => void; onCancel?: () => void
}) {
  const queryClient = useQueryClient()
  const canSeeSalary = useCan()('hr.view_salary')
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: employee?.first_name ?? '', last_name: employee?.last_name ?? '',
      document_type: employee?.document_type ?? 'CC', document_number: employee?.document_number ?? '',
      email: employee?.email ?? '', phone: employee?.phone ?? '', city: employee?.city ?? '',
      position: employee?.position ?? '', department: employee?.department ?? 'operations',
      hire_date: employee?.hire_date ?? '', salary: employee?.salary ?? '', status: employee?.status ?? 'active',
      notes: employee?.notes ?? '',
    },
  })
  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      // Sin permiso de salario no se envía el campo (el backend también lo ignoraría)
      const { salary, ...rest } = data
      const payload = canSeeSalary ? { ...rest, salary: salary || null } : rest
      return employee ? employeesApi.update(employee.id, payload) : employeesApi.create(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] })
      toast.success(employee ? 'Datos del empleado actualizados' : 'Empleado registrado')
      onSuccess()
    },
  })

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4" noValidate>
      <div className="grid sm:grid-cols-2 gap-4">
        <Input label="Nombre" required autoFocus {...register('first_name')} error={errors.first_name?.message} />
        <Input label="Apellido" required {...register('last_name')} error={errors.last_name?.message} />
      </div>
      <div className="grid sm:grid-cols-[180px_1fr] gap-4">
        <Select label="Documento" {...register('document_type')}>
          <option value="CC">Cédula de ciudadanía</option>
          <option value="CE">Cédula de extranjería</option>
          <option value="PP">Pasaporte</option>
        </Select>
        <Input label="Número de documento" required {...register('document_number')} error={errors.document_number?.message} />
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <Input label="Cargo" required placeholder="Panadero, cajera…" {...register('position')} error={errors.position?.message} />
        <Select label="Área" {...register('department')}>
          {DEPARTMENTS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
        </Select>
        <Input label="Fecha de ingreso" type="date" required {...register('hire_date')} error={errors.hire_date?.message} />
        {canSeeSalary && <Input label="Salario mensual (COP)" inputMode="numeric" {...register('salary')} />}
        <Input label="Email" type="email" {...register('email')} error={errors.email?.message} />
        <Input label="Teléfono" type="tel" {...register('phone')} />
        <Input label="Ciudad" {...register('city')} />
        <Select label="Estado" {...register('status')}>
          <option value="active">Activo</option>
          <option value="inactive">Inactivo</option>
        </Select>
      </div>
      <Textarea label="Notas" rows={2} {...register('notes')} />
      <FormActions error={mutation.isError ? getErrorMessage(mutation.error) : null} submitting={mutation.isPending}
                   submitLabel={employee ? 'Guardar cambios' : 'Registrar empleado'} onCancel={onCancel} />
    </form>
  )
}
