/**
 * Botón flotante (FAB) que abre/cierra el AssistantPanel.
 * Se posiciona en la esquina inferior derecha de la pantalla.
 */
import { useState } from 'react'
import { Sparkles, X } from 'lucide-react'
import AssistantPanel from './AssistantPanel'

export default function AssistantButton() {
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Panel — renderizado encima del botón */}
      {open && (
        <div className="fixed bottom-20 right-5 z-50 md:bottom-8 md:right-8">
          <AssistantPanel onClose={() => setOpen(false)} />
        </div>
      )}

      {/* FAB */}
      <button
        onClick={() => setOpen((v) => !v)}
        title={open ? 'Cerrar asistente' : 'Abrir asistente IA'}
        className={[
          'fixed bottom-5 right-5 md:bottom-6 md:right-6 z-50',
          'w-13 h-13 rounded-2xl flex items-center justify-center',
          'shadow-lg transition-all duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2',
          open
            ? 'bg-zinc-800 text-white hover:bg-zinc-700 dark:bg-zinc-700 dark:hover:bg-zinc-600 scale-95'
            : 'bg-gradient-to-br from-indigo-500 to-violet-600 text-white hover:scale-105 hover:shadow-indigo-500/40 active:scale-95',
        ].join(' ')}
        style={{ width: 52, height: 52 }}
      >
        <span className={['transition-all duration-200', open ? 'rotate-0' : 'rotate-0'].join(' ')}>
          {open ? <X size={20} /> : <Sparkles size={20} />}
        </span>

        {/* Pulse ring — solo cuando está cerrado */}
        {!open && (
          <span className="absolute inset-0 rounded-2xl bg-indigo-500 animate-ping opacity-20 pointer-events-none" />
        )}
      </button>
    </>
  )
}
