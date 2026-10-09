import { BrandMark } from '@/components/brand/Brand'

const POINTS = [
  'Cada empresa ve solo sus datos: aislamiento verificado en cada operación.',
  'Roles y permisos por persona, validados en el servidor.',
  'Registro de auditoría inalterable de lo que pasa en tu negocio.',
]

/** Layout de acceso: panel de marca (escritorio) + formulario. */
export default function AuthLayout({ title, subtitle, children }: { title: string; subtitle?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas flex">
      <aside className="hidden lg:flex lg:w-[42%] flex-col justify-between bg-primary text-primary-fg p-12">
        <div className="flex items-center gap-2.5">
          <BrandMark className="w-8 h-8 [&_rect]:fill-white/10" />
          <span className="text-lg font-semibold tracking-tight">GestorPro</span>
        </div>
        <div className="space-y-8 max-w-md">
          <div className="space-y-3">
            <h2 className="text-3xl font-semibold leading-tight tracking-tight">La operación de tu negocio, en orden.</h2>
            <p className="text-primary-fg/75 leading-relaxed">
              Ventas, clientes, productos y equipo en un solo lugar. Con <strong className="text-primary-fg">Miga</strong>, la
              versión especializada para panaderías.
            </p>
          </div>
          <ul className="space-y-3 text-sm text-primary-fg/80">
            {POINTS.map((p) => (
              <li key={p} className="flex gap-3"><span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent shrink-0" />{p}</li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-primary-fg/50">© {new Date().getFullYear()} GestorPro</p>
      </aside>

      <main className="flex-1 flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm space-y-7">
          <div className="lg:hidden flex items-center gap-2.5">
            <BrandMark /><span className="text-base font-semibold text-ink">GestorPro</span>
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-ink tracking-tight">{title}</h1>
            {subtitle && <p className="mt-1.5 text-sm text-ink-muted">{subtitle}</p>}
          </div>
          {children}
        </div>
      </main>
    </div>
  )
}
