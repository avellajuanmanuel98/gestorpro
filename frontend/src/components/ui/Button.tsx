import { forwardRef } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/cn'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
type Size = 'xs' | 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: React.ReactNode
  iconRight?: React.ReactNode
  fullWidth?: boolean
}

const variants: Record<Variant, string> = {
  primary: 'bg-primary text-primary-fg hover:bg-primary-hover',
  secondary: 'bg-surface-muted text-ink hover:bg-line',
  ghost: 'text-ink-muted hover:bg-surface-muted hover:text-ink',
  outline: 'border border-line-strong text-ink hover:bg-surface-muted',
  danger: 'bg-danger text-white hover:bg-danger-hover dark:text-canvas',
}

const sizes: Record<Size, string> = {
  xs: 'h-7 px-2.5 text-xs gap-1.5 rounded-md',
  sm: 'h-8 px-3 text-sm gap-1.5 rounded-lg',
  md: 'h-9 px-4 text-sm gap-2 rounded-lg',
  lg: 'h-11 px-5 text-base gap-2 rounded-xl',
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, icon, iconRight, fullWidth = false,
     children, disabled, className = '', type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center font-medium select-none whitespace-nowrap',
        'transition-colors duration-150 disabled:opacity-50 disabled:pointer-events-none',
        variants[variant], sizes[size], fullWidth && 'w-full', className,
      )}
      {...props}
    >
      {loading ? <Loader2 size={14} className="animate-spin shrink-0" /> : icon && <span className="shrink-0">{icon}</span>}
      {children && <span>{children}</span>}
      {!loading && iconRight && <span className="shrink-0">{iconRight}</span>}
    </button>
  ),
)

Button.displayName = 'Button'
export default Button
