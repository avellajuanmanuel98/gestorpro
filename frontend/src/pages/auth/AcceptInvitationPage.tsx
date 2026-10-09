import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { invitationApi } from '@/api/access'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
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
    mutationFn: () => invitationApi.accept({ token, password: form.password, first_name: form.first_name,
                                             last_name: form.last_name }),
    onSuccess: async (tokens) => { await startSession(tokens); navigate('/dashboard') },
  })

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }))

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')
    if (!preview.data?.account_exists && form.password !== form.password2) {
      setLocalError('Las contraseñas no coinciden.')
      return
    }
    accept.mutate()
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8 space-y-6">
        <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">GestorPro</p>

        {preview.isLoading ? <p className="text-sm text-zinc-500">Verificando invitación…</p> : preview.isError ? (
          <div className="space-y-3">
            <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Invitación no válida</h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              El enlace expiró, ya se usó o fue revocado. Pide a quien te invitó que genere uno nuevo.
            </p>
            <Link to="/login" className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Ir a iniciar sesión</Link>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                Únete a {preview.data!.tenant_name}
              </h1>
              <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                Te invitaron como <strong>{preview.data!.role_name}</strong> con el email {preview.data!.email}.
              </p>
            </div>

            {preview.data!.account_exists ? (
              <Input label="Tu contraseña de GestorPro" type="password" required autoFocus value={form.password}
                     onChange={set('password')} hint="Ya tienes una cuenta: confirma tu identidad para unirte." />
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Nombre" required autoFocus value={form.first_name} onChange={set('first_name')} />
                  <Input label="Apellido" value={form.last_name} onChange={set('last_name')} />
                </div>
                <Input label="Contraseña" type="password" required minLength={8} value={form.password} onChange={set('password')} />
                <Input label="Confirmar contraseña" type="password" required value={form.password2} onChange={set('password2')} />
              </>
            )}

            {(localError || accept.isError) && (
              <p role="alert" className="text-sm text-red-700 bg-red-50 dark:bg-red-950/40 dark:text-red-300 px-3 py-2 rounded-lg">
                {localError || getErrorMessage(accept.error)}
              </p>
            )}
            <Button type="submit" fullWidth loading={accept.isPending}>Aceptar invitación</Button>
          </form>
        )}
      </div>
    </div>
  )
}
