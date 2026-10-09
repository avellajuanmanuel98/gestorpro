import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '@/api/auth'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import AuthLayout from '@/layouts/AuthLayout'
import { getErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/authStore'

const EMPTY = { company_name: '', first_name: '', last_name: '', email: '', password: '', password2: '' }

export default function RegisterPage() {
  const navigate = useNavigate()
  const startSession = useAuthStore((s) => s.startSession)
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const set = (key: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.password2) { setError('Las contraseñas no coinciden.'); return }
    setLoading(true)
    try {
      // El backend crea la cuenta y la empresa (con la persona como propietaria) y valida la contraseña
      await startSession(await authApi.register(form))
      navigate('/dashboard')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Crea tu cuenta" subtitle="Empieza con 14 días de prueba. No necesitas tarjeta.">
      <form onSubmit={submit} className="space-y-4">
        <Input label="Nombre de tu empresa" required autoFocus value={form.company_name} onChange={set('company_name')}
               placeholder="Panadería La Favorita" />
        <div className="grid grid-cols-2 gap-3">
          <Input label="Nombre" required autoComplete="given-name" value={form.first_name} onChange={set('first_name')} />
          <Input label="Apellido" required autoComplete="family-name" value={form.last_name} onChange={set('last_name')} />
        </div>
        <Input label="Email" type="email" required autoComplete="email" value={form.email} onChange={set('email')} />
        <Input label="Contraseña" type="password" required minLength={8} autoComplete="new-password" value={form.password}
               onChange={set('password')} hint="Mínimo 8 caracteres; evita contraseñas comunes." />
        <Input label="Confirmar contraseña" type="password" required autoComplete="new-password" value={form.password2} onChange={set('password2')} />
        {error && <Alert>{error}</Alert>}
        <Button type="submit" fullWidth loading={loading} size="lg">Crear cuenta</Button>
      </form>
      <p className="text-sm text-ink-muted text-center">
        ¿Ya tienes cuenta? <Link to="/login" className="font-medium text-primary-ink hover:underline">Inicia sesión</Link>
      </p>
    </AuthLayout>
  )
}
