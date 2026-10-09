import { cn } from '@/lib/cn'

export type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'primary' | 'accent'

const variants: Record<BadgeVariant, string> = {
  default: 'bg-surface-muted text-ink-muted',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
  info: 'bg-info-soft text-info',
  primary: 'bg-primary-soft text-primary-ink',
  accent: 'bg-accent-soft text-accent-ink',
}

interface BadgeProps {
  variant?: BadgeVariant
  size?: 'sm' | 'md'
  dot?: boolean
  children: React.ReactNode
  className?: string
}

export default function Badge({ variant = 'default', size = 'sm', dot = false, children, className }: BadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap',
      size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-xs px-2.5 py-1',
      variants[variant], className,
    )}>
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current shrink-0" aria-hidden />}
      {children}
    </span>
  )
}
