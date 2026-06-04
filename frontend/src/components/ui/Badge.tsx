type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple'
type BadgeSize    = 'sm' | 'md'

interface BadgeProps {
  variant?: BadgeVariant
  size?:    BadgeSize
  dot?:     boolean
  children: React.ReactNode
  className?: string
}

const variants: Record<BadgeVariant, string> = {
  default: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300',
  success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400',
  warning: 'bg-amber-50  text-amber-700  dark:bg-amber-950/60  dark:text-amber-400',
  danger:  'bg-red-50    text-red-700    dark:bg-red-950/60    dark:text-red-400',
  info:    'bg-blue-50   text-blue-700   dark:bg-blue-950/60   dark:text-blue-400',
  purple:  'bg-violet-50 text-violet-700 dark:bg-violet-950/60 dark:text-violet-400',
}

const dotColors: Record<BadgeVariant, string> = {
  default: 'bg-zinc-400',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger:  'bg-red-500',
  info:    'bg-blue-500',
  purple:  'bg-violet-500',
}

const sizes: Record<BadgeSize, string> = {
  sm: 'text-xs px-2 py-0.5 gap-1.5',
  md: 'text-xs px-2.5 py-1 gap-1.5',
}

export default function Badge({
  variant   = 'default',
  size      = 'sm',
  dot       = false,
  children,
  className = '',
}: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center font-medium rounded-full',
        variants[variant],
        sizes[size],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {dot && (
        <span
          className={[
            'w-1.5 h-1.5 rounded-full shrink-0',
            dotColors[variant],
          ].join(' ')}
        />
      )}
      {children}
    </span>
  )
}
