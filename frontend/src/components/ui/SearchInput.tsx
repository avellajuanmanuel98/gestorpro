import { Search, X } from 'lucide-react'
import { controlClass } from './field'
import { cn } from '@/lib/cn'

export default function SearchInput({ value, onChange, placeholder, label }: {
  value: string; onChange: (value: string) => void; placeholder: string; label: string
}) {
  return (
    <div className="relative w-full sm:max-w-xs">
      <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle pointer-events-none" />
      <input type="search" aria-label={label} value={value} placeholder={placeholder}
             onChange={(e) => onChange(e.target.value)}
             className={cn(controlClass, 'h-9 pl-8 pr-8 border-line-strong [&::-webkit-search-cancel-button]:hidden')} />
      {value && (
        <button type="button" onClick={() => onChange('')} aria-label="Limpiar búsqueda"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-subtle hover:text-ink"><X size={14} /></button>
      )}
    </div>
  )
}
