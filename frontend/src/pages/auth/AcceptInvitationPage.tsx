import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { invitationApi } from '@/api/access'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { SkeletonText } from '@/components/ui/Skeleton'
import AuthLayout from '@/layouts/AuthLayout'
import { getErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/authStore'

export default function AcceptInvitationPage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const startSession = useAuthStore((s) => s.startSession)
  const [form, setForm] = useState({ first_name: '', last_name: '', password: '', password2: '' })
  const [localError, setLocalError] = useState('')

  const preview = useQuery({ queryKey: ['invitation', token], queryFn: () => invitationApi.preview(token), retry: false })
  const accept = useMutation({
    mutationFn: () => invitationApi.accept({ token, password: form.password, first_name: form.first_name, last_name: form.last_name }),
    onSuccess: async (tokens) => { await startSession(tokens); navigate('/dashboard') },
  })
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((p) => ({ ...p, [key]: e.target.value }))

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')
    if (!preview.data?.account_exists && form.password !== form.password2) { setLocalError('Las contraseñas no coinciden.'); return }
    accept.mutate()
  }

  if (preview.isLoading) return <AuthLayout title="Verificando invitación…"><SkeletonText lines={4} /></AuthLayout>
  if (preview.isError || !preview.data) {
    return (
      <AuthLayout title="Invitación no válida" subtitle="El enlace expiró, ya se usó o fue revocado.">
        <p className="text-sm text-ink-muted">Pide a quien te invitó que genere uno nuevo.</p>
        <Link to="/login" className="text-sm font-medium text-primary-ink hover:underline">Ir a iniciar sesión</Link>
      </AuthLayout>
    )
  }
  const inv = preview.data
  return (
    <AuthLayout title={`Únete a ${inv.tenant_name}`}
                subtitle={<>Te invitaron como <strong className="text-ink">{inv.role_name}</strong> con el email {inv.email}.</>}>
      <form onSubmit={submit} className="space-y-4">
        {inv.account_exists ? (
          <Input label="Tu contraseña de GestorPro" type="password" required autoFocus autoComplete="current-password"
                 value={form.password} onChange={set('password')} hint="Ya tienes una cuenta: confirma tu identidad para unirte." />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3">
              <Input label="Nombre" required autoFocus value={form.first_name} onChange={set('first_name')} />
              <Input label="Apellido" value={form.last_name} onChange={set('last_name')} />
            </div>
            <Input label="Crea una contraseña" type="password" required minLength={8} autoComplete="new-password"
                   value={form.password} onChange={set('password')} hint="Mínimo 8 caracteres." />
            <Input label="Confirmar contraseña" type="password" required autoComplete="new-password" value={form.password2} onChange={set('password2')} />
          </>
        )}
        {(localError || accept.isError) && <Alert>{localError || getErrorMessage(accept.error)}</Alert>}
        <Button type="submit" fullWidth size="lg" loading={accept.isPending}>Aceptar invitación</Button>
      </form>
    </AuthLayout>
  )
}
