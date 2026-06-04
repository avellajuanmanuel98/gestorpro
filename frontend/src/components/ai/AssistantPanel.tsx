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

function inlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g,   '<em>$1</em>')
    .replace(/`(.*?)`/g,     '<code class="bg-black/10 dark:bg-white/10 px-1 py-0.5 rounded text-xs font-mono">$1</code>')
}

// ── Message bubble ─────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser      = message.role === 'user'
  const isStreaming  = message.streaming === true

  return (
    <div className={['flex gap-3 animate-fade-up', isUser ? 'flex-row-reverse' : ''].join(' ')}>
      {/* Avatar */}
      {!isUser && (
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0 mt-0.5 shadow-sm shadow-indigo-500/30">
          <Sparkles size={12} className="text-white" />
        </div>
      )}

      {/* Bubble */}
      <div
        className={[
          'max-w-[82%] px-3.5 py-2.5 rounded-2xl',
          isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm shadow-sm shadow-indigo-600/20'
            : message.error
            ? 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/30 dark:text-red-300 dark:border-red-800/50 rounded-tl-sm'
            : 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100 rounded-tl-sm',
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
          <span className="inline-block w-0.5 h-3.5 bg-indigo-500 dark:bg-indigo-400 ml-0.5 animate-pulse rounded-full" />
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
    } catch (err: any) {
      if (err?.name === 'AbortError') {
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
      'bg-white dark:bg-zinc-900',
      'border border-zinc-200 dark:border-zinc-800',
      'rounded-2xl shadow-2xl shadow-black/20 dark:shadow-black/60',
      'overflow-hidden',
      'animate-scale-in',
      'w-[380px] h-[560px]',
    ].join(' ')}>

      {/* ── Header ── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-100 dark:border-zinc-800 shrink-0 bg-gradient-to-r from-indigo-600 to-violet-600">
        <div className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center shrink-0">
          <Sparkles size={14} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white leading-none">Asistente GestorPro</p>
          <p className="text-xs text-indigo-200 mt-0.5">Powered by Claude</p>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              title="Limpiar conversación"
              className="p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
            >
              <RotateCcw size={14} />
            </button>
          )}
          <button
            onClick={onClose}
            title="Cerrar"
            className="p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
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
          <div className="flex flex-col items-center justify-center h-full text-center space-y-5 animate-fade-up">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Sparkles size={24} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Hola, soy tu asistente de negocio
              </p>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-[240px] leading-relaxed">
                Tengo acceso a los datos reales de tu empresa. Pregúntame lo que quieras.
              </p>
            </div>
            {/* Quick suggestions */}
            <div className="w-full space-y-2">
              <p className="text-[11px] font-medium text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
                Sugerencias
              </p>
              <div className="grid grid-cols-1 gap-1.5">
                {SUGGESTIONS.slice(0, 4).map((s) => (
                  <button
                    key={s}
                    onClick={() => sendMessage(s)}
                    className={[
                      'text-left text-xs px-3 py-2 rounded-lg',
                      'bg-zinc-50 hover:bg-indigo-50 dark:bg-zinc-800/60 dark:hover:bg-indigo-950/40',
                      'text-zinc-700 hover:text-indigo-700 dark:text-zinc-300 dark:hover:text-indigo-300',
                      'border border-zinc-200 hover:border-indigo-200 dark:border-zinc-700 dark:hover:border-indigo-800',
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
            className="p-1.5 rounded-full bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 shadow-md text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all animate-fade-up"
          >
            <ChevronDown size={14} />
          </button>
        </div>
      )}

      {/* ── Input area ── */}
      <div className="shrink-0 px-3 pb-3 pt-2 border-t border-zinc-100 dark:border-zinc-800">
        <div className={[
          'flex items-end gap-2 rounded-xl border px-3 py-2',
          'bg-zinc-50 dark:bg-zinc-800/60',
          'border-zinc-200 dark:border-zinc-700',
          'focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-500/15',
          'transition-all duration-150',
        ].join(' ')}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={streaming}
            placeholder="Escribe tu pregunta…"
            rows={1}
            className={[
              'flex-1 bg-transparent text-sm resize-none outline-none',
              'text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 dark:placeholder:text-zinc-500',
              'leading-relaxed max-h-[120px] overflow-y-auto',
              'disabled:opacity-50',
            ].join(' ')}
          />
          {streaming ? (
            <button
              onClick={handleStop}
              title="Detener"
              className="shrink-0 p-1.5 rounded-lg bg-red-100 text-red-600 hover:bg-red-200 dark:bg-red-950/50 dark:text-red-400 dark:hover:bg-red-950 transition-colors"
            >
              <StopCircle size={16} />
            </button>
          ) : (
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim()}
              title="Enviar (Enter)"
              className={[
                'shrink-0 p-1.5 rounded-lg transition-all duration-150',
                input.trim()
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm shadow-indigo-600/20'
                  : 'bg-zinc-200 text-zinc-400 dark:bg-zinc-700 dark:text-zinc-500 cursor-not-allowed',
              ].join(' ')}
            >
              <SendHorizonal size={15} />
            </button>
          )}
        </div>
        <p className="text-[10px] text-zinc-400 dark:text-zinc-600 text-center mt-1.5">
          Enter para enviar · Shift+Enter para nueva línea
        </p>
      </div>
    </div>
  )
}
