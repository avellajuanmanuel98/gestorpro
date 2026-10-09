import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, Save, Loader2 } from 'lucide-react'
import { tenantApi } from '@/api/auth'
import { formatDate } from '@/lib/dates'
import { useAuthStore, useCan } from '@/store/authStore'
import type { Tenant } from '@/types'
import { getErrorMessage } from '@/lib/errors'

export default function CompanyPage() {
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(false)
  const canEdit = useCan()('tenant.manage')
  const refreshSession = useAuthStore((s) => s.refreshSession)

  // Datos de la empresa ACTIVA (el endpoint no recibe ids)
  const { data: company, isLoading } = useQuery({
    queryKey: ['tenant'],
    queryFn:  tenantApi.current,
  })
  const { data: plan } = useQuery({ queryKey: ['tenant-plan'], queryFn: tenantApi.plan })

  // Estado local del formulario — se inicializa cuando llegan los datos
  const [form, setForm] = useState<Partial<Tenant>>({})

  // Sincronizamos el form cuando llegan los datos de la API
  // (solo la primera vez, para no pisar lo que el usuario ya escribió)
  const formData: Partial<Tenant> = {
    name:    form.name    ?? company?.name    ?? '',
    email:   form.email   ?? company?.email   ?? '',
    phone:   form.phone   ?? company?.phone   ?? '',
    tax_id:  form.tax_id  ?? company?.tax_id  ?? '',
    city:    form.city    ?? company?.city    ?? '',
    address: form.address ?? company?.address ?? '',
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  // Mutación para guardar — usamos PATCH para enviar solo los campos que cambiaron
  const mutation = useMutation({
    mutationFn: () => tenantApi.update(formData),
    onSuccess: (updated) => {
      queryClient.setQueryData(['tenant'], updated)
      void refreshSession()  // el nombre de la empresa aparece en la navegación
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <Loader2 className="animate-spin text-indigo-500" size={32} />
      </div>
    )
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">

      {/* Encabezado */}
      <div className="flex items-center gap-3 mb-6">
        <Building2 className="text-indigo-600" size={24} />
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Mi Empresa</h1>
          <p className="text-sm text-gray-500">Información y configuración de tu empresa</p>
        </div>
      </div>

      {/* Plan (solo lectura: lo administra GestorPro) */}
      {plan?.plan.name && (
        <section className="bg-white rounded-xl border border-gray-200 p-5 mb-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Plan actual</p>
              <p className="text-base font-semibold text-gray-900">{plan.plan.name}</p>
            </div>
            {plan.plan.status === 'trialing' && (
              <span className="text-xs font-medium bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-full">
                En prueba hasta el {formatDate(plan.plan.trial_ends_at)}
              </span>
            )}
          </div>
          <dl className="grid grid-cols-2 gap-4">
            {plan.limits.map((l) => {
              const pct = l.limit ? Math.min(100, Math.round((l.used / l.limit) * 100)) : 0
              return (
                <div key={l.key}>
                  <dt className="text-xs text-gray-500">{l.label}</dt>
                  <dd className="text-sm font-medium text-gray-900 tabular-nums">
                    {l.used} de {l.limit === null ? 'ilimitado' : l.limit}
                  </dd>
                  {l.limit !== null && l.limit > 0 && (
                    <div className="mt-1 h-1.5 rounded-full bg-gray-100 overflow-hidden" aria-hidden>
                      <div className={`h-full rounded-full ${pct >= 100 ? 'bg-amber-500' : 'bg-indigo-500'}`}
                           style={{ width: `${pct}%` }} />
                    </div>
                  )}
                </div>
              )
            })}
          </dl>
        </section>
      )}

      {!canEdit && (
        <p className="mb-4 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
          Solo los administradores pueden editar los datos de la empresa.
        </p>
      )}

      {/* Formulario */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <fieldset disabled={!canEdit} className="space-y-5 disabled:opacity-70">

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nombre de la empresa <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">NIT / RUT</label>
            <input
              type="text"
              name="tax_id"
              value={formData.tax_id}
              onChange={handleChange}
              placeholder="900123456-7"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ciudad</label>
            <input
              type="text"
              name="city"
              value={formData.city}
              onChange={handleChange}
              placeholder="Bogotá"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Correo de contacto
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="contacto@empresa.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
            <input
              type="text"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              placeholder="601 234 5678"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Dirección</label>
          <input
            type="text"
            name="address"
            value={formData.address}
            onChange={handleChange}
            placeholder="Calle 123 # 45-67"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>

        {/* Feedback de error */}
        {mutation.isError && (
          <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          {getErrorMessage(mutation.error)}
        </p>
        )}

        {/* Feedback de éxito */}
        {saved && (
          <p className="text-sm text-green-700 bg-green-50 px-3 py-2 rounded-lg">
            Cambios guardados correctamente.
          </p>
        )}

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending
              ? <><Loader2 size={16} className="animate-spin" /> Guardando...</>
              : <><Save size={16} /> Guardar cambios</>
            }
          </button>
        </div>
        </fieldset>
      </form>
    </div>
  )
}
