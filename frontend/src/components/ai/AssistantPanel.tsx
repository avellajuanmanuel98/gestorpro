/**
 * Panel de chat del asistente IA de GestorPro.
 *
 * Features:
 * - Streaming en tiempo real (texto aparece letra por letra)
 * - Historial de conversación en memoria
 * - Sugerencias rápidas para onboarding
 * - Diseño premium: dark/light mode, animaciones, scroll auto
 * - Cancelación de requests en curso
 * - Renderizado de markdown básico (negritas, listas, saltos de línea)
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  X, SendHorizonal, Sparkles, StopCircle,
  RotateCcw, ChevronDown,
} from 'lucide-react'
import { streamAssistantMessage } from '@/api/assistant'
import { inlineMarkdown } from '@/lib/markdown'

// ── Types ──────────────────────────────────────────────────────────────────────

type Role = 'user' | 'assistant'

interface Message {
  id:        string
  role:      Role
  content:   string
  streaming?: boolean
  error?:    boolean
}

// ── Quick suggestions ──────────────────────────────────────────────────────────

const SUGGESTIONS = [
  '¿Cuánto he recaudado este mes?',
  '¿Cuántas facturas tengo vencidas?',
  '¿Cuál es mi tasa de cobro actual?',
  '¿Cómo están mis ingresos este año?',
  'Dame un resumen de mi negocio',
  '¿Cuántos clientes activos tengo?',
]

// ── Markdown-lite renderer ─────────────────────────────────────────────────────

function renderMarkdown(text: string): React.ReactNode {
  // Split by newlines and render basic markdown
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let listBuffer: string[] = []

  const flushList = (key: string) => {
    if (listBuffer.length > 0) {
      elements.push(
        <ul key={`ul-${key}`} className="mt-1.5 space-y-1 pl-4">
          {listBuffer.map((item, i) => (
            <li key={i} className="flex gap-2 text-sm leading-relaxed">
              <span className="shrink-0 mt-1.5 w-1 h-1 rounded-full bg-current opacity-60" />
              <span dangerouslySetInnerHTML={{ __html: inlineMarkdown(item) }} />
            </li>
          ))}
        </ul>
      )
      listBuffer = []
    }
  }

  lines.forEach((line, i) => {
    const trimmed = line.trim()
    if (!trimmed) {
      flushList(`e${i}`)
      return
    }
    // Bullet list
    if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      listBuffer.push(trimmed.slice(2))
      return
    }
    flushList(`b${i}`)
    // Regular paragraph
    elements.push(
      <p
        key={i}
        className="text-sm leading-relaxed"
        dangerouslySetInnerHTML={{ __html: inlineMarkdown(trimmed) }}
      />
    )
  })
  flushList('end')

  return <div className="space-y-1.5">{elements}</div>
}

// ── Message bubble ─────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser      = message.role === 'user'
  const isStreaming  = message.streaming === true

  return (
    <div className={['flex gap-3 animate-fade-in', isUser ? 'flex-row-reverse' : ''].join(' ')}>
      {/* Avatar */}
      {!isUser && (
        <div className="w-7 h-7 rounded-lg bg-primary-soft text-primary-ink flex items-center justify-center shrink-0 mt-0.5">
          <Sparkles size={12} />
        </div>
      )}

      {/* Bubble */}
      <div
        className={[
          'max-w-[82%] px-3.5 py-2.5 rounded-2xl',
          isUser
            ? 'bg-primary text-primary-fg rounded-tr-sm'
            : message.error
            ? 'bg-danger-soft text-danger rounded-tl-sm'
            : 'bg-surface-muted text-ink rounded-tl-sm',
        ].join(' ')}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed">{message.content}</p>
        ) : message.error ? (
          <p className="text-sm leading-relaxed">{message.content}</p>
        ) : (
          renderMarkdown(message.content)
        )}

        {/* Typing cursor */}
        {isStreaming && !isUser && (
          <span className="inline-block w-0.5 h-3.5 bg-primary ml-0.5 animate-pulse rounded-full" />
        )}
      </div>
    </div>
  )
}

// ── Main panel ─────────────────────────────────────────────────────────────────

interface AssistantPanelProps {
  onClose: () => void
}

export default function AssistantPanel({ onClose }: AssistantPanelProps) {
  const [messages,    setMessages]    = useState<Message[]>([])
  const [input,       setInput]       = useState('')
  const [streaming,   setStreaming]   = useState(false)
  const [showScrollBtn, setShowScrollBtn] = useState(false)

  const bottomRef    = useRef<HTMLDivElement>(null)
  const inputRef     = useRef<HTMLTextAreaElement>(null)
  const scrollRef    = useRef<HTMLDivElement>(null)
  const abortRef     = useRef<AbortController | null>(null)
  const msgIdCounter = useRef(0)

  const nextId = () => String(++msgIdCounter.current)

  // Auto-scroll
  const scrollToBottom = useCallback((smooth = true) => {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'instant' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages.length, scrollToBottom])

  // Detect if user scrolled up
  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60
    setShowScrollBtn(!isAtBottom)
  }

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
  }

  // Send message
  const sendMessage = useCallback(async (text: string) => {
    const userText = text.trim()
    if (!userText || streaming) return

    setInput('')
    if (inputRef.current) inputRef.current.style.height = 'auto'

    // Add user message
    const userMsg: Message = { id: nextId(), role: 'user', content: userText }
    setMessages((prev) => [...prev, userMsg])

    // Placeholder for assistant
    const assistantId = nextId()
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: 'assistant', content: '', streaming: true },
    ])
    setStreaming(true)

    // Abort controller for cancel
    const controller = new AbortController()
    abortRef.current = controller

    try {
      await streamAssistantMessage(
        userText,
        {
          onDelta: (chunk) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + chunk }
                  : m
              )
            )
            scrollToBottom()
          },
          onDone: () => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, streaming: false } : m
              )
            )
            setStreaming(false)
          },
          onError: (errMsg) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: errMsg, streaming: false, error: true }
                  : m
              )
            )
            setStreaming(false)
          },
        },
        controller.signal
      )
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: m.content || '_(Cancelado)_', streaming: false }
              : m
          )
        )
      }
      setStreaming(false)
    }
  }, [streaming, scrollToBottom])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleStop = () => {
    abortRef.current?.abort()
  }

  const handleClear = () => {
    if (streaming) abortRef.current?.abort()
    setMessages([])
    setStreaming(false)
  }

  const isEmpty = messages.length === 0

  return (
    <div className={[
      'flex flex-col',
      'bg-surface',
      'border border-line',
      'rounded-2xl shadow-overlay',
      'overflow-hidden',
      'animate-pop-in',
      'w-[min(92vw,380px)] h-[min(75vh,560px)]',
    ].join(' ')}>

      {/* ── Header ── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-line shrink-0">
        <div className="w-7 h-7 rounded-lg bg-primary-soft text-primary-ink flex items-center justify-center shrink-0">
          <Sparkles size={14} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-ink leading-none">Asistente</p>
          <p className="text-xs text-ink-muted mt-0.5">IA con los datos de tu empresa</p>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              title="Limpiar conversación"
              aria-label="Limpiar conversación"
              className="p-1.5 rounded-lg text-ink-subtle hover:text-ink hover:bg-surface-muted transition-colors"
            >
              <RotateCcw size={14} />
            </button>
          )}
          <button
            onClick={onClose}
            title="Cerrar"
            aria-label="Cerrar asistente"
            className="p-1.5 rounded-lg text-ink-subtle hover:text-ink hover:bg-surface-muted transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* ── Messages ── */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scroll-smooth"
      >
        {isEmpty ? (
          /* Welcome screen */
          <div className="flex flex-col items-center justify-center h-full text-center space-y-5 animate-fade-in">
            <div className="w-12 h-12 rounded-xl bg-primary-soft text-primary-ink flex items-center justify-center">
              <Sparkles size={22} />
            </div>
            <div>
              <p className="text-sm font-semibold text-ink">
                Hola, soy tu asistente de negocio
              </p>
              <p className="text-xs text-ink-muted mt-1 max-w-[240px] leading-relaxed">
                Respondo con los datos de tu empresa. Puedo equivocarme: verifica las cifras importantes.
              </p>
            </div>
            {/* Quick suggestions */}
            <div className="w-full space-y-2">
              <p className="text-[11px] font-medium text-ink-subtle uppercase tracking-wider">
                Sugerencias
              </p>
              <div className="grid grid-cols-1 gap-1.5">
                {SUGGESTIONS.slice(0, 4).map((s) => (
                  <button
                    key={s}
                    onClick={() => sendMessage(s)}
                    className={[
                      'text-left text-xs px-3 py-2 rounded-lg',
                      'bg-surface-muted hover:bg-primary-soft',
                      'text-ink-muted hover:text-primary-ink',
                      'border border-line',
                      'transition-all duration-150',
                    ].join(' ')}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}
        <div ref={bottomRef} />
      </div>

      {/* Scroll-to-bottom button */}
      {showScrollBtn && (
        <div className="absolute bottom-[76px] right-6">
          <button
            onClick={() => scrollToBottom()}
            aria-label="Ir al último mensaje"
            className="p-1.5 rounded-full bg-surface border border-line shadow-overlay text-ink-muted hover:text-ink transition-colors"
          >
            <ChevronDown size={14} />
          </button>
        </div>
      )}

      {/* ── Input area ── */}
      <div className="shrink-0 px-3 pb-3 pt-2 border-t border-line">
        <div className={[
          'flex items-end gap-2 rounded-xl border px-3 py-2',
          'bg-surface-muted',
          'border-line',
          'focus-within:border-focus focus-within:ring-2 focus-within:ring-focus/20',
          'transition-all duration-150',
        ].join(' ')}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={streaming}
            aria-label="Pregunta para el asistente"
            placeholder="Escribe tu pregunta…"
            rows={1}
            className={[
              'flex-1 bg-transparent text-sm resize-none outline-none',
              'text-ink placeholder:text-ink-subtle',
              'leading-relaxed max-h-[120px] overflow-y-auto',
              'disabled:opacity-50',
            ].join(' ')}
          />
          {streaming ? (
            <button
              onClick={handleStop}
              title="Detener"
              aria-label="Detener respuesta"
              className="shrink-0 p-1.5 rounded-lg bg-danger-soft text-danger transition-colors"
            >
              <StopCircle size={16} />
            </button>
          ) : (
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim()}
              title="Enviar (Enter)"
              aria-label="Enviar pregunta"
              className={[
                'shrink-0 p-1.5 rounded-lg transition-colors duration-150',
                input.trim() ? 'bg-primary text-primary-fg hover:bg-primary-hover' : 'bg-line text-ink-subtle cursor-not-allowed',
              ].join(' ')}
            >
              <SendHorizonal size={15} />
            </button>
          )}
        </div>
        <p className="text-[10px] text-ink-subtle text-center mt-1.5">
          Enter para enviar · Shift+Enter para nueva línea
        </p>
      </div>
    </div>
  )
}
