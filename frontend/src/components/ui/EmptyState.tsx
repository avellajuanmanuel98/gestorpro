import Button from './Button'

interface EmptyStateProps {
  icon?:        React.ReactNode
  title:        string
  description?: string
  action?:      {
    label:   string
    onClick: () => void
    icon?:   React.ReactNode
  }
  size?: 'sm' | 'md' | 'lg'
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
  size = 'md',
}: EmptyStateProps) {
  const paddingMap = { sm: 'py-8', md: 'py-16', lg: 'py-24' }
  const iconSizeMap = { sm: 'w-10 h-10', md: 'w-14 h-14', lg: 'w-16 h-16' }

  return (
    <div
      className={[
        'flex flex-col items-center justify-center text-center px-6',
        paddingMap[size],
      ].join(' ')}
    >
      {icon && (
        <div
          className={[
            'flex items-center justify-center rounded-2xl mb-4',
            'bg-zinc-100 dark:bg-zinc-800 text-zinc-400 dark:text-zinc-500',
            iconSizeMap[size],
          ].join(' ')}
        >
          {icon}
        </div>
      )}

      <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
        {title}
      </h3>

      {description && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-xs leading-relaxed">
          {description}
        </p>
      )}

      {action && (
        <div className="mt-5">
          <Button
            variant="primary"
            size="sm"
            onClick={action.onClick}
            icon={action.icon}
          >
            {action.label}
          </Button>
        </div>
      )}
    </div>
  )
}
