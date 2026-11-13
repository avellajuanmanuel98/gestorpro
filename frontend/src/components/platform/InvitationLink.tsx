import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import Button from '@/components/ui/Button'
import { copyText } from '@/lib/clipboard'

/** El enlace de invitación solo se muestra una vez: se copia y se envía al dueño. */
export default function InvitationLink({ url, hint }: { url: string; hint?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="space-y-2">
      <p className="text-sm text-ink-muted">{hint ?? 'Envíale este enlace al dueño para que cree su contraseña. Vence en 7 días y no se vuelve a mostrar.'}</p>
      <div className="flex gap-2">
        <input readOnly value={url} aria-label="Enlace" onFocus={(e) => e.target.select()}
               className="flex-1 min-w-0 h-9 rounded-lg border border-line-strong bg-surface-muted px-3 text-sm text-ink" />
        <Button type="button" variant="outline" icon={copied ? <Check size={14} /> : <Copy size={14} />}
                onClick={async () => setCopied(await copyText(url))}>{copied ? 'Copiado' : 'Copiar'}</Button>
      </div>
    </div>
  )
}
