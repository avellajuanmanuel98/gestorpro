import Button from './Button'

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: React.ReactNode
  action?: { label: string; onClick: () => void; icon?: React.ReactNode }
  compact?: boolean
}

/** Estado vacío: explica por qué no hay datos y qué hacer a continuación. */
export default function EmptyState({ icon, title, description, action, compact = false }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center text-center px-6 ${compact ? 'py-8' : 'py-14'}`}>
      {icon && (
        <div className="flex items-center justify-center w-11 h-11 rounded-xl mb-3 bg-surface-muted text-ink-subtle">{icon}</div>
      )}
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {description && <p className="mt-1 text-sm text-ink-muted max-w-sm leading-relaxed">{description}</p>}
      {action && (
        <div className="mt-4">
          <Button size="sm" onClick={action.onClick} icon={action.icon}>{action.label}</Button>
        </div>
      )}
    </div>
  )
}
