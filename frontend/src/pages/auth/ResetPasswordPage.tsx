import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { authApi } from '@/api/auth'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { SkeletonText } from '@/components/ui/Skeleton'
import AuthLayout from '@/layouts/AuthLayout'
import { getErrorMessage } from '@/lib/errors'
import { toast } from '@/store/toastStore'

/** Enlace de un solo uso (correo, dueño o soporte): la persona escribe su contraseña nueva. */
export default function ResetPasswordPage() {
  const { uid = '', token = '' } = useParams()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const check = useQuery({ queryKey: ['reset', uid, token], queryFn: () => authApi.checkReset(uid, token), retry: false })
  const save = useMutation({
    mutationFn: () => authApi.resetPassword(uid, token, password, password2),
    onSuccess: () => { toast.success('Contraseña nueva guardada. Ya puedes entrar.'); navigate('/login', { replace: true }) },
  })
  if (check.isLoading) return <AuthLayout title="Verificando el enlace…"><SkeletonText lines={3} /></AuthLayout>
  if (!check.data?.valid) {
    return (
      <AuthLayout title="El enlace ya no sirve" subtitle="Venció (dura 24 horas) o ya se usó.">
        <Link to="/forgot-password" className="block text-center text-sm text-primary-ink hover:underline">Pedir un enlace nuevo</Link>
      </AuthLayout>
    )
  }
  return (
    <AuthLayout title="Crea tu contraseña nueva" subtitle={`Para la cuenta ${check.data.email}.`}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        <Input label="Contraseña nueva" type="password" autoComplete="new-password" required autoFocus value={password}
               onChange={(e) => setPassword(e.target.value)} hint="Mínimo 12 caracteres; evita contraseñas comunes." />
        <Input label="Repítela" type="password" autoComplete="new-password" required value={password2}
               onChange={(e) => setPassword2(e.target.value)} />
        {save.isError && <Alert>{getErrorMessage(save.error)}</Alert>}
        <Button type="submit" fullWidth size="lg" loading={save.isPending}>Guardar contraseña</Button>
      </form>
    </AuthLayout>
  )
}
