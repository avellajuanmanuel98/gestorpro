import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { Eye, EyeOff } from 'lucide-react'
import { authApi } from '@/api/auth'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import AuthLayout from '@/layouts/AuthLayout'
import { useAuthStore } from '@/store/authStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const startSession = useAuthStore((s) => s.startSession)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await startSession(await authApi.login(email, password))
      navigate('/dashboard')
    } catch (err) {
      if (isAxiosError(err) && !err.response) setError('No se puede conectar con el servidor. Verifica tu conexión.')
      else if (isAxiosError(err) && err.response?.status === 429) setError('Demasiados intentos. Espera un minuto e inténtalo de nuevo.')
      else if (isAxiosError(err) && err.response?.status === 400) setError('Email o contraseña incorrectos.')
      else setError('El servidor no está disponible. Intenta de nuevo en unos minutos.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Inicia sesión" subtitle="Ingresa con el email de tu cuenta.">
      <form onSubmit={submit} className="space-y-4">
        <Input label="Email" type="email" autoComplete="email" required autoFocus value={email}
               onChange={(e) => setEmail(e.target.value)} placeholder="tu@empresa.com" />
        <Input label="Contraseña" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required
               value={password} onChange={(e) => setPassword(e.target.value)}
               rightIcon={
                 <button type="button" onClick={() => setShowPassword((v) => !v)} className="hover:text-ink pointer-events-auto"
                         aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>
                   {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                 </button>
               } />
        {error && <Alert>{error}</Alert>}
        <Button type="submit" fullWidth loading={loading} size="lg">Entrar</Button>
      </form>
      <p className="text-sm text-ink-muted text-center">
        ¿Tu empresa aún no usa GestorPro? <Link to="/register" className="font-medium text-primary-ink hover:underline">Crea una cuenta</Link>
      </p>
    </AuthLayout>
  )
}
