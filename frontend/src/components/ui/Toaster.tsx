import { CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/cn'
import { useToastStore } from '@/store/toastStore'

const icons = { success: CheckCircle2, error: XCircle, info: Info }
const tones = { success: 'text-success', error: 'text-danger', info: 'text-info' }

/** Región de avisos. Se monta una vez en App. */
export default function Toaster() {
  const { toasts, dismiss } = useToastStore()
  return createPortal(
    <div aria-live="polite" className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[60] flex flex-col gap-2 w-[min(92vw,380px)]">
      {toasts.map((t) => {
        const Icon = icons[t.tone]
        return (
          <div key={t.id} role={t.tone === 'error' ? 'alert' : 'status'}
               className="flex items-start gap-3 bg-surface border border-line rounded-xl shadow-overlay px-4 py-3 animate-pop-in">
            <Icon size={18} className={cn('shrink-0 mt-px', tones[t.tone])} />
            <p className="flex-1 text-sm text-ink">{t.message}</p>
            <button type="button" onClick={() => dismiss(t.id)} aria-label="Cerrar aviso"
                    className="text-ink-subtle hover:text-ink"><X size={14} /></button>
          </div>
        )
      })}
    </div>,
    document.body,
  )
}
