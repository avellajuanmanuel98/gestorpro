import { cn } from '@/lib/cn'

interface CardProps extends React.HTMLAttributes<HTMLElement> {
  as?: 'section' | 'div' | 'article'
  padded?: boolean
}

/** Superficie base: plana, borde de 1px, sin sombra. */
export function Card({ as: Tag = 'section', padded = false, className, ...props }: CardProps) {
  return <Tag className={cn('bg-surface border border-line rounded-xl', padded && 'p-5', className)} {...props} />
}

export function CardHeader({ title, description, actions }: { title: string; description?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 px-5 pt-4 pb-3">
      <div>
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {description && <div className="text-xs text-ink-muted mt-0.5">{description}</div>}
      </div>
      {actions}
    </div>
  )
}
