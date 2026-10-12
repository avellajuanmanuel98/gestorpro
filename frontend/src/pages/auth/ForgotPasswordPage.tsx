import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '@/api/auth'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import AuthLayout from '@/layouts/AuthLayout'
import { getErrorMessage } from '@/lib/errors'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const send = useMutation({ mutationFn: () => authApi.forgotPassword(email) })
  const done = send.data
  return (
    <AuthLayout title="¿Olvidaste tu contraseña?" subtitle="Te ayudamos a crear una nueva. Nadie más la conocerá.">
      {done ? (
        <div className="space-y-4">
          {done.email_enabled ? (
            <Alert tone="success">
              Si <strong>{email}</strong> tiene una cuenta, le llegará un correo con un enlace para crear una contraseña nueva.
              Revisa también la carpeta de spam. El enlace vence en 24 horas.
            </Alert>
          ) : (
            <Alert tone="info">
              Esta instalación no envía correos. Pídele al <strong>dueño o administrador de tu empresa</strong> un
              "enlace de contraseña nueva": lo genera en Configuración → Usuarios. Si eres el dueño, pídeselo al soporte de GestorPro.
            </Alert>
          )}
          <Link to="/login" className="block text-center text-sm text-primary-ink hover:underline">Volver a iniciar sesión</Link>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); send.mutate() }}>
          <Input label="Email de tu cuenta" type="email" autoComplete="email" required autoFocus value={email}
                 onChange={(e) => setEmail(e.target.value)} placeholder="tu@empresa.com" />
          {send.isError && <Alert>{getErrorMessage(send.error)}</Alert>}
          <Button type="submit" fullWidth size="lg" loading={send.isPending}>Continuar</Button>
          <Link to="/login" className="block text-center text-sm text-ink-muted hover:text-ink">Volver</Link>
        </form>
      )}
    </AuthLayout>
  )
}
