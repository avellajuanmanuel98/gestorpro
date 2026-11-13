import { cn } from '@/lib/cn'

/** Interruptor de encendido/apagado (role=switch). */
export default function Switch({ checked, onChange, label, disabled }: {
  checked: boolean; onChange: (next: boolean) => void; label: string; disabled?: boolean
}) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled}
            onClick={() => onChange(!checked)}
            className={cn('relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50',
              checked ? 'bg-primary' : 'bg-line-strong')}>
      <span className={cn('absolute top-0.5 h-5 w-5 rounded-full bg-surface shadow transition-all', checked ? 'left-[22px]' : 'left-0.5')} />
    </button>
  )
}
