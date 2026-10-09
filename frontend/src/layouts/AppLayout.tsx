import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeftRight, BarChart2, Boxes, Building2, FileText, History, KeyRound, LayoutDashboard,
  LogOut, Menu, Moon, Sun, Truck, UserCheck, UserCog, Users, X,
} from 'lucide-react'
import Brand from '@/components/brand/Brand'
import { cn } from '@/lib/cn'
import { useAuthStore, useCan, useHasFeature } from '@/store/authStore'
import { useThemeStore } from '@/store/themeStore'

// ── Navegación ────────────────────────────────────────────────────────────────
// `permission` y `feature` solo adaptan la UI: el backend exige ambos.

interface NavItem {
  to: string
  icon: React.ElementType
  label: string
  permission?: string
  feature?: string
}

const navGroups: { label: string; items: NavItem[] }[] = [
  {
    label: 'Operación',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Inicio' },
      { to: '/clients', icon: Users, label: 'Clientes', permission: 'customers.view' },
      { to: '/invoices', icon: FileText, label: 'Facturación', permission: 'billing.view' },
      { to: '/inventory', icon: Boxes, label: 'Productos', permission: 'catalog.view' },
    ],
  },
  {
    label: 'Gestión',
    items: [
      { to: '/suppliers', icon: Truck, label: 'Proveedores', permission: 'suppliers.view' },
      { to: '/employees', icon: UserCheck, label: 'Personal', permission: 'hr.view', feature: 'module.hr' },
      { to: '/reports', icon: BarChart2, label: 'Reportes', permission: 'reports.view' },
    ],
  },
  {
    label: 'Configuración',
    items: [
      { to: '/company', icon: Building2, label: 'Empresa', permission: 'tenant.view' },
      { to: '/users', icon: UserCog, label: 'Usuarios', permission: 'access.view' },
      { to: '/roles', icon: KeyRound, label: 'Roles', permission: 'access.view' },
      { to: '/audit', icon: History, label: 'Auditoría', permission: 'audit.view' },
    ],
  },
]

const routeLabels: Record<string, string> = Object.fromEntries(
  navGroups.flatMap((g) => g.items.map((i) => [i.to, i.label])),
)

function initials(name?: string) {
  return (name ?? '?').split(' ').filter(Boolean).slice(0, 2).map((n) => n[0]).join('').toUpperCase() || '?'
}

function Avatar({ name }: { name?: string }) {
  return (
    <span className="w-8 h-8 rounded-full bg-surface-muted border border-line text-ink-muted text-xs font-semibold flex items-center justify-center shrink-0">
      {initials(name)}
    </span>
  )
}

function TenantSwitcher() {
  const session = useAuthStore((s) => s.session)
  const switchTenant = useAuthStore((s) => s.switchTenant)
  const queryClient = useQueryClient()
  const [switching, setSwitching] = useState(false)
  if (!session?.tenant) return null
  const others = session.memberships.filter((m) => m.tenant_id !== session.tenant?.id)

  const handleSwitch = async (tenantId: number) => {
    setSwitching(true)
    try {
      await switchTenant(tenantId)
      queryClient.clear() // ningún dato en caché de la empresa anterior
    } finally {
      setSwitching(false)
    }
  }

  return (
    <div className="mx-3 mb-4 rounded-lg border border-line bg-surface-muted/50 px-3 py-2.5">
      <p className="text-sm font-medium text-ink truncate" title={session.tenant.name}>{session.tenant.name}</p>
      <p className="text-xs text-ink-muted truncate">{session.role?.name}{session.plan?.name ? ` · Plan ${session.plan.name}` : ''}</p>
      {others.length > 0 && (
        <label className="mt-2 flex items-center gap-1.5 text-xs text-ink-muted">
          <ArrowLeftRight size={12} className="shrink-0" />
          <span className="sr-only">Cambiar de empresa</span>
          <select value="" disabled={switching}
                  onChange={(e) => e.target.value && void handleSwitch(Number(e.target.value))}
                  className="w-full bg-transparent focus:outline-none cursor-pointer">
            <option value="">Cambiar de empresa…</option>
            {others.map((m) => <option key={m.tenant_id} value={m.tenant_id}>{m.tenant_name}</option>)}
          </select>
        </label>
      )}
    </div>
  )
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const session = useAuthStore((s) => s.session)
  const logout = useAuthStore((s) => s.logout)
  const can = useCan()
  const hasFeature = useHasFeature()
  const { theme, toggleTheme } = useThemeStore()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const handleLogout = async () => {
    await logout() // revoca el refresh token en el servidor
    queryClient.clear()
    navigate('/login')
  }

  const groups = navGroups
    .map((g) => ({ ...g, items: g.items.filter((i) => (!i.permission || can(i.permission)) && (!i.feature || hasFeature(i.feature))) }))
    .filter((g) => g.items.length > 0)

  return (
    <div className="flex flex-col h-full">
      <div className="h-16 flex items-center px-5 shrink-0">
        <Brand vertical={session?.tenant?.vertical} />
      </div>
      <TenantSwitcher />

      <nav aria-label="Principal" className="flex-1 overflow-y-auto px-3 pb-4 space-y-5">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="px-2.5 mb-1 text-[11px] font-medium text-ink-subtle">{group.label}</p>
            <ul className="space-y-0.5">
              {group.items.map(({ to, icon: Icon, label }) => (
                <li key={to}>
                  <NavLink to={to} onClick={onNavigate}
                    className={({ isActive }) => cn(
                      'relative flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors',
                      isActive
                        ? 'bg-primary-soft text-primary-ink font-medium before:absolute before:left-0 before:top-2 before:bottom-2 before:w-0.5 before:rounded-full before:bg-accent'
                        : 'text-ink-muted hover:bg-surface-muted hover:text-ink',
                    )}>
                    <Icon size={16} className="shrink-0" />
                    <span className="truncate">{label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-line p-3 space-y-1">
        <button type="button" onClick={toggleTheme}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm text-ink-muted hover:bg-surface-muted hover:text-ink transition-colors">
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          {theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
        </button>
        <div className="flex items-center gap-2.5 px-2.5 py-2">
          <Avatar name={session?.user.full_name} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink truncate leading-tight">{session?.user.full_name || 'Usuario'}</p>
            <p className="text-xs text-ink-muted truncate">{session?.user.email}</p>
          </div>
          <button type="button" onClick={() => void handleLogout()} aria-label="Cerrar sesión" title="Cerrar sesión"
                  className="p-1.5 rounded-lg text-ink-subtle hover:text-danger hover:bg-danger-soft transition-colors">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const vertical = useAuthStore((s) => s.session?.tenant?.vertical)
  const currentLabel = routeLabels[location.pathname] ?? ''

  return (
    <div className="flex h-screen bg-canvas overflow-hidden">
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-line bg-surface">
        <Sidebar />
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40 animate-fade-in" onClick={() => setSidebarOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 bg-surface border-r border-line flex flex-col animate-slide-in">
            <button type="button" onClick={() => setSidebarOpen(false)} aria-label="Cerrar menú"
                    className="absolute top-4 right-3 p-1.5 rounded-lg text-ink-muted hover:bg-surface-muted">
              <X size={16} />
            </button>
            <Sidebar onNavigate={() => setSidebarOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden h-14 shrink-0 bg-surface border-b border-line flex items-center gap-3 px-4">
          <button type="button" onClick={() => setSidebarOpen(true)} aria-label="Abrir menú"
                  className="p-1.5 -ml-1.5 rounded-lg text-ink-muted hover:bg-surface-muted">
            <Menu size={18} />
          </button>
          <Brand vertical={vertical} compact />
          <span className="text-sm font-medium text-ink truncate">{currentLabel}</span>
        </header>

        <main className="flex-1 overflow-auto">
          <div key={location.pathname} className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
