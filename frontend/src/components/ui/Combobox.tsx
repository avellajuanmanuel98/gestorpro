import { useId, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react'
import { cn } from '@/lib/cn'
import { useDebounced } from '@/lib/useDebounced'
import { controlClass, errorClass, labelClass } from './field'

export interface ComboOption {
  id: number
  label: string
  description?: string
}

interface ComboboxProps {
  label?: string
  value: ComboOption | null
  onChange: (option: ComboOption | null) => void
  /** Búsqueda en el servidor: no carga listas completas en el navegador */
  search: (term: string) => Promise<ComboOption[]>
  queryKey: string
  placeholder?: string
  error?: string
  required?: boolean
}

/** Selector con búsqueda (ARIA combobox): teclado ↑ ↓ Enter Escape. */
export default function Combobox({ label, value, onChange, search, queryKey, placeholder = 'Buscar…', error, required }: ComboboxProps) {
  const id = useId()
  const listId = `${id}-list`
  const [open, setOpen] = useState(false)
  const [term, setTerm] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const debounced = useDebounced(term)

  const { data: options = [], isFetching } = useQuery({
    queryKey: [queryKey, 'search', debounced],
    queryFn: () => search(debounced),
    enabled: open,
    staleTime: 30_000,
  })

  const choose = (option: ComboOption) => {
    onChange(option)
    setTerm('')
    setOpen(false)
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((i) => Math.min(i + 1, options.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter' && open && options[active]) { e.preventDefault(); choose(options[active]) }
    else if (e.key === 'Escape') { setOpen(false); setTerm('') }
  }

  return (
    <div className="space-y-1.5 relative">
      {label && (
        <label htmlFor={id} className={labelClass}>
          {label}{required && <span className="text-danger ml-0.5" aria-hidden>*</span>}
        </label>
      )}
      <div className="relative">
        <input
          ref={inputRef}
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={open && options[active] ? `${id}-opt-${options[active].id}` : undefined}
          aria-invalid={error ? true : undefined}
          autoComplete="off"
          value={open ? term : value?.label ?? ''}
          placeholder={value ? value.label : placeholder}
          onChange={(e) => { setTerm(e.target.value); setOpen(true); setActive(0) }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          onKeyDown={onKeyDown}
          className={cn(controlClass, 'h-9 pl-3 pr-9', error ? 'border-danger' : 'border-line-strong')}
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-subtle pointer-events-none">
          {isFetching ? <Loader2 size={14} className="animate-spin" /> : <ChevronsUpDown size={14} />}
        </span>
      </div>
      {open && (
        <ul id={listId} role="listbox"
            className="absolute z-30 mt-1 w-full max-h-64 overflow-auto bg-surface border border-line rounded-lg shadow-overlay py-1">
          {options.length === 0 && !isFetching && (
            <li className="px-3 py-2 text-sm text-ink-muted">{debounced ? 'Sin resultados' : 'Escribe para buscar'}</li>
          )}
          {options.map((option, index) => (
            <li
              key={option.id}
              id={`${id}-opt-${option.id}`}
              role="option"
              aria-selected={value?.id === option.id}
              onMouseDown={(e) => { e.preventDefault(); choose(option) }}
              onMouseEnter={() => setActive(index)}
              className={cn('flex items-center justify-between gap-3 px-3 py-2 text-sm cursor-pointer',
                index === active ? 'bg-surface-muted' : '')}
            >
              <span className="min-w-0">
                <span className="block text-ink truncate">{option.label}</span>
                {option.description && <span className="block text-xs text-ink-muted truncate">{option.description}</span>}
              </span>
              {value?.id === option.id && <Check size={14} className="text-primary-ink shrink-0" />}
            </li>
          ))}
        </ul>
      )}
      {error && <p className={errorClass}>{error}</p>}
    </div>
  )
}
