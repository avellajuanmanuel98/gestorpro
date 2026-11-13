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
        <div className="fixed bottom-20 right-5 z-50 md:right-6">
          <AssistantPanel onClose={() => setOpen(false)} />
        </div>
      )}

      {/* FAB */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? 'Cerrar asistente' : 'Abrir asistente de IA'}
        aria-expanded={open}
        className={[
          'fixed bottom-5 right-5 md:bottom-6 md:right-6 z-50 w-12 h-12 rounded-full flex items-center justify-center',
          'shadow-overlay transition-colors duration-150',
          open ? 'bg-ink text-canvas' : 'bg-primary text-primary-fg hover:bg-primary-hover',
        ].join(' ')}
      >
        {open ? <X size={20} /> : <Sparkles size={20} />}
      </button>
    </>
  )
}
