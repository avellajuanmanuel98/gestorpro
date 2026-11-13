interface PageHeaderProps {
  title: string
  description?: React.ReactNode
  actions?: React.ReactNode
}

export default function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold text-ink tracking-tight">{title}</h1>
        {description && <p className="text-sm text-ink-muted mt-1">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

/** Contenedor estándar de página: ancho máximo y espaciado consistentes. */
export function Page({ children, width = 'wide' }: { children: React.ReactNode; width?: 'narrow' | 'wide' }) {
  return (
    <div className={`px-4 py-6 md:px-8 md:py-8 space-y-6 mx-auto ${width === 'narrow' ? 'max-w-3xl' : 'max-w-7xl'}`}>
      {children}
    </div>
  )
}
