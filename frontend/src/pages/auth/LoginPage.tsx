import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import Button from '@/components/ui/Button'

export default function LoginPage() {
  const navigate  = useNavigate()
  const setUser   = useAuthStore((s) => s.setUser)

  const [email,       setEmail]       = useState('')
  const [password,    setPassword]    = useState('')
  const [showPass,    setShowPass]    = useState(false)
  const [error,       setError]       = useState('')
  const [loading,     setLoading]     = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const tokens = await authApi.login(email, password)
      localStorage.setItem('access_token',  tokens.access)
      localStorage.setItem('refresh_token', tokens.refresh)
      const user = await authApi.getProfile()
      setUser(user)
      navigate('/dashboard')
    } catch (err: any) {
      if (err.message === 'Network Error') {
        setError('No se puede conectar con el servidor. Verifica que el backend esté activo.')
      } else {
        setError('Email o contraseña incorrectos. Intenta de nuevo.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex transition-colors duration-300">

      {/* ── Left panel — branding (hidden on mobile) ── */}
      <div className="hidden lg:flex lg:w-[45%] xl:w-1/2 relative bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-800 flex-col justify-between p-12 overflow-hidden">

        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-32 -right-32 w-96 h-96 bg-white/5 rounded-full blur-3xl" />
          <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-violet-500/20 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-indigo-500/10 rounded-full blur-2xl" />

          {/* Grid pattern */}
          <div className="absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage: 'linear-gradient(rgba(255,255,255,0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.8) 1px, transparent 1px)',
              backgroundSize: '48px 48px',
            }}
          />
        </div>

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center border border-white/20">
            <span className="text-white text-base font-bold">G</span>
          </div>
          <span className="text-white text-lg font-semibold tracking-tight">GestorPro</span>
        </div>

        {/* Hero text */}
        <div className="relative space-y-6">
          <div className="space-y-3">
            <h1 className="text-3xl xl:text-4xl font-bold text-white leading-tight tracking-tight">
              Gestiona tu negocio<br />con claridad total.
            </h1>
            <p className="text-indigo-200 text-base leading-relaxed max-w-sm">
              Clientes, facturas, inventario y reportes — todo en un solo lugar, diseñado para PYMEs colombianas.
            </p>
          </div>

          {/* Feature pills */}
          <div className="flex flex-wrap gap-2">
            {['Facturación', 'CRM', 'Inventario', 'Reportes', 'Multi-empresa'].map((f) => (
              <span key={f} className="px-3 py-1 text-xs font-medium bg-white/10 text-indigo-100 rounded-full border border-white/15 backdrop-blur-sm">
                {f}
              </span>
            ))}
          </div>
        </div>

        {/* Bottom quote */}
        <div className="relative">
          <p className="text-indigo-200/70 text-xs">
            © 2026 GestorPro · Hecho en Colombia 🇨🇴
          </p>
        </div>
      </div>

      {/* ── Right panel — form ── */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm animate-fade-up">

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2.5 mb-10">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-sm shadow-indigo-500/30">
              <span className="text-white text-sm font-bold">G</span>
            </div>
            <span className="text-base font-semibold text-zinc-900 dark:text-zinc-100">GestorPro</span>
          </div>

          {/* Heading */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 tracking-tight">
              Bienvenido de nuevo
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1.5">
              Inicia sesión en tu cuenta para continuar.
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Email */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Correo electrónico
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="correo@empresa.com"
                className={[
                  'w-full h-10 px-3 text-sm rounded-lg border',
                  'bg-white dark:bg-zinc-900/60',
                  'text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 dark:placeholder:text-zinc-500',
                  'border-zinc-200 dark:border-zinc-700',
                  'focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-400 dark:focus:border-indigo-500',
                  'transition-all duration-150',
                ].join(' ')}
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Contraseña
                </label>
                <a href="#" className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
                  ¿Olvidaste tu contraseña?
                </a>
              </div>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className={[
                    'w-full h-10 pl-3 pr-10 text-sm rounded-lg border',
                    'bg-white dark:bg-zinc-900/60',
                    'text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 dark:placeholder:text-zinc-500',
                    'border-zinc-200 dark:border-zinc-700',
                    'focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-400 dark:focus:border-indigo-500',
                    'transition-all duration-150',
                  ].join(' ')}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
                >
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2.5 p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800/50 rounded-lg animate-fade-down">
                <AlertCircle size={15} className="text-red-500 dark:text-red-400 shrink-0 mt-0.5" />
                <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
              </div>
            )}

            {/* Submit */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              loading={loading}
              iconRight={!loading ? <ArrowRight size={16} /> : undefined}
            >
              Iniciar sesión
            </Button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
            <span className="text-xs text-zinc-400 dark:text-zinc-600">¿nuevo aquí?</span>
            <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
          </div>

          {/* Register link */}
          <Link
            to="/register"
            className={[
              'flex items-center justify-center gap-2 w-full h-10 rounded-lg text-sm font-medium',
              'border border-zinc-200 dark:border-zinc-700',
              'text-zinc-700 dark:text-zinc-300',
              'hover:bg-zinc-50 dark:hover:bg-zinc-800/60 hover:border-zinc-300 dark:hover:border-zinc-600',
              'transition-all duration-150',
            ].join(' ')}
          >
            Crear una cuenta gratis
          </Link>
        </div>
      </div>
    </div>
  )
}
