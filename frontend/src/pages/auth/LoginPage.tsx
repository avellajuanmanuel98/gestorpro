import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { authApi, isMfaChallenge } from '@/api/auth'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import AuthLayout from '@/layouts/AuthLayout'
import { getErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/authStore'

function loginError(err: unknown): string {
  if (isAxiosError(err) && !err.response) return 'No se puede conectar con el servidor. Verifica tu conexión.'
  const status = isAxiosError(err) ? err.response?.status : undefined
  if (status === 400) return 'Email o contraseña incorrectos.'
  if (status === 429 || status === 403) return getErrorMessage(err, 'Demasiados intentos. Espera un minuto e inténtalo de nuevo.')
  return 'El servidor no está disponible. Intenta de nuevo en unos minutos.'
}

export default function LoginPage() {
  const navigate = useNavigate()
  const startSession = useAuthStore((s) => s.startSession)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  // Personal de la plataforma: segundo paso con el código de la app autenticadora
  const [mfaToken, setMfaToken] = useState<string | null>(null)
  const [code, setCode] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const result = await authApi.login(email, password)
      if (isMfaChallenge(result)) {
        setMfaToken(result.mfa_token)
        return
      }
      await startSession(result)
      navigate('/')
    } catch (err) {
      setError(loginError(err))
    } finally {
      setLoading(false)
    }
  }

  const verify = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await startSession(await authApi.verifyMfa(mfaToken!, code))
      navigate('/')
    } catch (err) {
      const expired = isAxiosError(err) && (err.response?.data as { code?: string } | undefined)?.code === 'mfa_expired'
      if (expired) { setMfaToken(null); setCode('') }
      setError(isAxiosError(err) && err.response ? getErrorMessage(err) : loginError(err))
    } finally {
      setLoading(false)
    }
  }

  if (mfaToken) {
    return (
      <AuthLayout title="Verificación en dos pasos" subtitle="Escribe el código de 6 dígitos que muestra tu app autenticadora.">
        <form onSubmit={verify} className="space-y-4">
          <Input label="Código" inputMode="numeric" autoComplete="one-time-code" required autoFocus maxLength={7}
                 value={code} onChange={(e) => setCode(e.target.value.replace(/[^0-9 ]/g, ''))} placeholder="123 456"
                 leftIcon={<ShieldCheck size={15} />} />
          {error && <Alert>{error}</Alert>}
          <Button type="submit" fullWidth loading={loading} size="lg" disabled={code.replace(/\D/g, '').length !== 6}>
            Verificar
          </Button>
          <p className="text-center">
            <button type="button" className="text-sm text-primary-ink hover:underline"
                    onClick={() => { setMfaToken(null); setCode(''); setError('') }}>
              Volver
            </button>
          </p>
        </form>
      </AuthLayout>
    )
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
        <p className="text-center"><Link to="/forgot-password" className="text-sm text-primary-ink hover:underline">¿Olvidaste tu contraseña?</Link></p>
      </form>
      <p className="text-sm text-ink-muted text-center">
        ¿Tu empresa aún no usa GestorPro? <Link to="/register" className="font-medium text-primary-ink hover:underline">Crea una cuenta</Link>
      </p>
    </AuthLayout>
  )
}
