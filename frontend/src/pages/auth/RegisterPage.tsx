import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'

// Estructura del formulario
interface FormData {
  company_name: string
  first_name:   string
  last_name:    string
  email:        string
  password:     string
  password2:    string
}

const EMPTY_FORM: FormData = {
  company_name: '',
  first_name:   '',
  last_name:    '',
  email:        '',
  password:     '',
  password2:    '',
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const setUser  = useAuthStore((s) => s.setUser)

  const [form,    setForm]    = useState<FormData>(EMPTY_FORM)
  const [error,   setError]   = useState<string>('')
  const [loading, setLoading] = useState(false)

  // Actualizamos un campo del formulario de forma genérica
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validación básica en el cliente antes de llamar a la API
    if (form.password !== form.password2) {
      setError('Las contraseñas no coinciden.')
      return
    }
    if (form.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.')
      return
    }

    setLoading(true)
    try {
      // 1. Registramos — el backend crea empresa + usuario admin
      await authApi.register(form)

      // 2. Hacemos login automático con las credenciales recién creadas
      const tokens = await authApi.login(form.email, form.password)
      localStorage.setItem('access_token',  tokens.access)
      localStorage.setItem('refresh_token', tokens.refresh)

      // 3. Cargamos perfil y guardamos en Zustand
      const user = await authApi.getProfile()
      setUser(user)

      // 4. Al dashboard
      navigate('/dashboard')
    } catch (err: any) {
      // Imprimimos en consola para debugging (F12 → Console)
      console.error('Register error:', err)

      if (err.response?.data) {
        // El backend devuelve errores como { email: ['...'], password: ['...'] }
        const data = err.response.data
        // Puede ser un objeto con listas, o un objeto con string, o un string directo
        if (typeof data === 'string') {
          setError(data)
        } else if (data.detail) {
          setError(data.detail)
        } else {
          const msgs = Object.values(data).flat() as string[]
          setError(msgs.join(' '))
        }
      } else if (err.message === 'Network Error') {
        setError('No se puede conectar con el servidor. ¿Está corriendo el backend en localhost:8000?')
      } else {
        setError(`Error: ${err.message ?? 'Intenta de nuevo.'}`)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        {/* Encabezado */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-indigo-600">GestorPro</h1>
          <p className="text-gray-500 mt-2">Crea tu empresa y empieza gratis</p>
        </div>

        {/* Tarjeta */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Crear cuenta</h2>

          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Nombre de empresa — va primero porque es lo más importante */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre de tu empresa
              </label>
              <input
                type="text"
                name="company_name"
                value={form.company_name}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Ej: Ferretería El Tornillo"
              />
            </div>

            {/* Nombre y apellido en fila */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre
                </label>
                <input
                  type="text"
                  name="first_name"
                  value={form.first_name}
                  onChange={handleChange}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Juan"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Apellido
                </label>
                <input
                  type="text"
                  name="last_name"
                  value={form.last_name}
                  onChange={handleChange}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="García"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Correo electrónico
              </label>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="correo@empresa.com"
              />
            </div>

            {/* Contraseñas */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña
              </label>
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Mínimo 8 caracteres"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirmar contraseña
              </label>
              <input
                type="password"
                name="password2"
                value={form.password2}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Repite la contraseña"
              />
            </div>

            {/* Errores */}
            {error && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creando cuenta...' : 'Crear cuenta gratis'}
            </button>
          </form>

          {/* Link al login */}
          <p className="text-center text-sm text-gray-500 mt-6">
            ¿Ya tienes cuenta?{' '}
            <Link to="/login" className="text-indigo-600 hover:underline font-medium">
              Inicia sesión
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
