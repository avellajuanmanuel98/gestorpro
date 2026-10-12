import { useState } from 'react'
import { Navigate, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Building, Gauge, History, Layers, LogOut, Menu, Moon, Sun, X } from 'lucide-react'
import { BrandMark } from '@/components/brand/Brand'
import { cn } from '@/lib/cn'
import { useAuthStore } from '@/store/authStore'
import { useThemeStore } from '@/store/themeStore'

const NAV = [
  { to: '/platform', icon: Gauge, label: 'Resumen', end: true },
  { to: '/platform/tenants', icon: Building, label: 'Empresas' },
  { to: '/platform/plans', icon: Layers, label: 'Planes' },
  { to: '/platform/events', icon: History, label: 'Bitácora' },
]

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const session = useAuthStore((s) => s.session)
  const logout = useAuthStore((s) => s.logout)
  const { theme, toggleTheme } = useThemeStore()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  return (
    <div className="flex flex-col h-full">
      <div className="h-16 flex items-center gap-2.5 px-5 shrink-0">
        <BrandMark isMiga={false} />
        <div className="leading-none">
          <p className="text-[15px] font-semibold tracking-tight text-ink">GestorPro</p>
          <p className="mt-0.5 text-[10px] font-medium tracking-wide text-accent">PLATAFORMA</p>
        </div>
      </div>
      <nav aria-label="Plataforma" className="flex-1 overflow-y-auto px-3 pb-4">
        <ul className="space-y-0.5">
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <li key={to}>
              <NavLink to={to} end={end} onClick={onNavigate}
                className={({ isActive }) => cn(
                  'relative flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-primary-soft text-primary-ink font-medium before:absolute before:left-0 before:top-2 before:bottom-2 before:w-0.5 before:rounded-full before:bg-accent'
                    : 'text-ink-muted hover:bg-surface-muted hover:text-ink',
                )}>
                <Icon size={16} className="shrink-0" /><span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="shrink-0 border-t border-line p-3 space-y-1">
        {session?.tenant && (
          <NavLink to="/dashboard" onClick={onNavigate}
                   className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm text-ink-muted hover:bg-surface-muted hover:text-ink">
            <ArrowLeft size={16} /> Volver a {session.tenant.name}
          </NavLink>
        )}
        <button type="button" onClick={toggleTheme}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm text-ink-muted hover:bg-surface-muted hover:text-ink">
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}{theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
        </button>
        <div className="flex items-center gap-2.5 px-2.5 py-2">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink truncate">{session?.user.full_name || 'Equipo GestorPro'}</p>
            <p className="text-xs text-ink-muted truncate">{session?.user.email}</p>
          </div>
          <button type="button" aria-label="Cerrar sesión" title="Cerrar sesión"
                  onClick={async () => { await logout(); queryClient.clear(); navigate('/login') }}
                  className="p-1.5 rounded-lg text-ink-subtle hover:text-danger hover:bg-danger-soft"><LogOut size={15} /></button>
        </div>
      </div>
    </div>
  )
}

/** Consola del personal de GestorPro. Separada de la app de las empresas. */
export default function PlatformLayout() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const session = useAuthStore((s) => s.session)
  if (!session?.user.is_platform_admin) return <Navigate to="/" replace />
  if (session.support) return <Navigate to="/dashboard" replace />  // en soporte se navega la empresa
  return (
    <div className="flex h-screen bg-canvas overflow-hidden">
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-line bg-surface"><Sidebar /></aside>
      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 bg-surface border-r border-line flex flex-col">
            <button type="button" onClick={() => setOpen(false)} aria-label="Cerrar menú"
                    className="absolute top-4 right-3 p-1.5 rounded-lg text-ink-muted hover:bg-surface-muted"><X size={16} /></button>
            <Sidebar onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden h-14 shrink-0 bg-surface border-b border-line flex items-center gap-3 px-4">
          <button type="button" onClick={() => setOpen(true)} aria-label="Abrir menú"
                  className="p-1.5 -ml-1.5 rounded-lg text-ink-muted hover:bg-surface-muted"><Menu size={18} /></button>
          <span className="text-sm font-semibold text-ink">GestorPro · Plataforma</span>
        </header>
        <main className="flex-1 overflow-auto">
          <div key={location.pathname} className="page-enter"><Outlet /></div>
        </main>
      </div>
    </div>
  )
}
