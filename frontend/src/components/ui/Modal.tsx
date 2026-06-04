import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

interface ModalProps {
  title:     string
  isOpen:    boolean
  onClose:   () => void
  children:  React.ReactNode
  size?:     'sm' | 'md' | 'lg' | 'xl'
  subtitle?: string
}

const sizes = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}

export default function Modal({
  title,
  isOpen,
  onClose,
  children,
  size = 'md',
  subtitle,
}: ModalProps) {
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div
      className="modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />

      {/* Panel */}
      <div
        ref={contentRef}
        onClick={(e) => e.stopPropagation()}
        className={[
          'modal-content relative bg-white dark:bg-zinc-900',
          'border border-zinc-200 dark:border-zinc-800',
          'rounded-2xl shadow-2xl shadow-black/20 dark:shadow-black/60',
          'w-full max-h-[90vh] flex flex-col',
          sizes[size],
        ].join(' ')}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-5 pb-4 border-b border-zinc-100 dark:border-zinc-800 shrink-0">
          <div>
            <h2
              id="modal-title"
              className="text-base font-semibold text-zinc-900 dark:text-zinc-100"
            >
              {title}
            </h2>
            {subtitle && (
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Cerrar modal"
            className={[
              'p-1.5 rounded-lg transition-colors shrink-0 ml-4',
              'text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100',
              'dark:text-zinc-500 dark:hover:text-zinc-300 dark:hover:bg-zinc-800',
            ].join(' ')}
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-6 py-5">
          {children}
        </div>
      </div>
    </div>
  )
}
