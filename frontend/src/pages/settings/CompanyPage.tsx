import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, Save, Loader2 } from 'lucide-react'
import { authApi } from '@/api/auth'
import type { Company } from '@/types'

export default function CompanyPage() {
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(false)

  // Cargamos los datos de la empresa
  const { data: company, isLoading } = useQuery({
    queryKey: ['my-company'],
    queryFn:  authApi.getMyCompany,
  })

  // Estado local del formulario — se inicializa cuando llegan los datos
  const [form, setForm] = useState<Partial<Company>>({})

  // Sincronizamos el form cuando llegan los datos de la API
  // (solo la primera vez, para no pisar lo que el usuario ya escribió)
  const formData: Partial<Company> = {
    name:    form.name    ?? company?.name    ?? '',
    email:   form.email   ?? company?.email   ?? '',
    phone:   form.phone   ?? company?.phone   ?? '',
    nit:     form.nit     ?? company?.nit     ?? '',
    city:    form.city    ?? company?.city    ?? '',
    address: form.address ?? company?.address ?? '',
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  // Mutación para guardar — usamos PATCH para enviar solo los campos que cambiaron
  const mutation = useMutation({
    mutationFn: () => authApi.updateMyCompany(formData),
    onSuccess: (updated) => {
      // Actualizamos la caché de React Query con los datos nuevos
      queryClient.setQueryData(['my-company'], updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate()
  }

  // Plan badge — muestra el plan actual con un color
  const planColors = {
    free:    'bg-gray-100 text-gray-600',
    starter: 'bg-blue-100 text-blue-600',
    pro:     'bg-indigo-100 text-indigo-700',
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

      {/* Plan actual (solo lectura) */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">Plan actual</p>
          <p className="text-base font-medium text-gray-900 capitalize">{company?.plan}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${planColors[company?.plan ?? 'free']}`}>
          {company?.plan?.toUpperCase()}
        </span>
      </div>

      {/* Formulario */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">

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
              name="nit"
              value={formData.nit}
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
            Ocurrió un error al guardar. Intenta de nuevo.
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
      </form>
    </div>
  )
}
