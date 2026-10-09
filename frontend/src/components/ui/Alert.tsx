import { cn } from '@/lib/cn'

/** Mensaje en línea (errores de formulario, avisos de contexto). */
export default function Alert({ tone = 'danger', children, className }: {
  tone?: 'danger' | 'warning' | 'info' | 'success'; children: React.ReactNode; className?: string
}) {
  const tones = {
    danger: 'bg-danger-soft text-danger', warning: 'bg-warning-soft text-warning',
    info: 'bg-info-soft text-info', success: 'bg-success-soft text-success',
  }
  return (
    <div role={tone === 'danger' ? 'alert' : 'status'} className={cn('text-sm rounded-lg px-3 py-2', tones[tone], className)}>
      {children}
    </div>
  )
}
