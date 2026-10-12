import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Eye, LogOut } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

const minutesLeft = (iso: string) => Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 60000))

/**
 * Aviso permanente mientras el personal de GestorPro ve una empresa en modo soporte.
 * Es solo lectura: el servidor rechaza cualquier cambio.
 */
export default function SupportBanner() {
  const support = useAuthStore((s) => s.session?.support)
  const tenantName = useAuthStore((s) => s.session?.tenant?.name)
  const exitSupport = useAuthStore((s) => s.exitSupport)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [left, setLeft] = useState(() => (support ? minutesLeft(support.expires_at) : 0))
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    if (!support) return
    const timer = window.setInterval(() => setLeft(minutesLeft(support.expires_at)), 15000)
    return () => window.clearInterval(timer)
  }, [support])

  if (!support) return null
  const leave = async () => {
    setLeaving(true)
    const tenantId = await exitSupport()
    queryClient.clear()
    navigate(tenantId ? `/platform/tenants/${tenantId}` : '/platform', { replace: true })
  }
  return (
    <div role="status" className="shrink-0 bg-ink text-canvas px-4 py-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <Eye size={15} className="shrink-0" aria-hidden />
      <span className="font-medium">Modo soporte · solo lectura</span>
      <span className="opacity-80 min-w-0 truncate">{tenantName} · {left} min restantes · motivo: {support.reason}</span>
      <button type="button" onClick={() => void leave()} disabled={leaving}
              className="ml-auto inline-flex items-center gap-1.5 h-7 px-3 rounded-lg bg-canvas/15 hover:bg-canvas/25 text-canvas font-medium">
        <LogOut size={14} /> Salir del soporte
      </button>
    </div>
  )
}
