import { cn } from '@/lib/cn'

interface TabsProps<T extends string> {
  tabs: { id: T; label: string; count?: number }[]
  value: T
  onChange: (id: T) => void
  label: string
}

/** Pestañas (role=tablist) con flechas izquierda/derecha. */
export default function Tabs<T extends string>({ tabs, value, onChange, label }: TabsProps<T>) {
  const onKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    const next = (index + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length
    onChange(tabs[next].id)
  }
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 border-b border-line">
      {tabs.map((tab, index) => {
        const selected = tab.id === value
        return (
          <button key={tab.id} type="button" role="tab" aria-selected={selected} tabIndex={selected ? 0 : -1}
                  onClick={() => onChange(tab.id)} onKeyDown={(e) => onKeyDown(e, index)}
                  className={cn('relative px-3 py-2 text-sm font-medium transition-colors -mb-px border-b-2',
                    selected ? 'border-primary text-ink' : 'border-transparent text-ink-muted hover:text-ink')}>
            {tab.label}
            {tab.count !== undefined && <span className="ml-1.5 text-xs text-ink-subtle num">{tab.count}</span>}
          </button>
        )
      })}
    </div>
  )
}
