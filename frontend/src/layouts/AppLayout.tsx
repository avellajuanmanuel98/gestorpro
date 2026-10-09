import { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Users, FileText, Building2, LogOut,
  Menu, X, UserCheck, Truck, BarChart2, Boxes,
  Moon, Sun, ChevronRight, ArrowLeftRight, KeyRound, History, UserCog,
} from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore, useCan, useHasFeature } from '@/store/authStore'
import { useThemeStore } from '@/store/themeStore'

// ── Navigation config ─────────────────────────────────────────────────────────
// `permission`: solo se muestra el módulo si el rol lo incluye. Es una ayuda de
// UX; el backend rechaza igualmente cualquier acceso no permitido.

interface NavItem {
  to:          string
  icon:        React.ElementType
  label:       string
  permission?: string
  /** Funcionalidad del plan requerida (el backend también la exige) */
  feature?:    string
}

const navGroups: { label: string; items: NavItem[] }[] = [
  {
    label: 'Principal',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard'                                  },
      { to: '/clients',   icon: Users,           label: 'Clientes',    permission: 'customers.view' },
      { to: '/invoices',  icon: FileText,        label: 'Facturación', permission: 'billing.view'   },
      { to: '/inventory', icon: Boxes,           label: 'Inventario',  permission: 'catalog.view'   },
    ],
  },
  {
    label: 'Recursos',
    items: [
      { to: '/employees', icon: UserCheck, label: 'Empleados',   permission: 'hr.view', feature: 'module.hr' },
      { to: '/suppliers', icon: Truck,     label: 'Proveedores', permission: 'suppliers.view' },
      { to: '/reports',   icon: BarChart2, label: 'Reportes',    permission: 'reports.view'   },
    ],
  },
  {
    label: 'Configuración',
    items: [
      { to: '/company', icon: Building2, label: 'Mi Empresa', permission: 'tenant.view' },
      { to: '/users',   icon: UserCog,   label: 'Usuarios',   permission: 'access.view' },
      { to: '/roles',   icon: KeyRound,  label: 'Roles',      permission: 'access.view' },
      { to: '/audit',   icon: History,   label: 'Auditoría',  permission: 'audit.view'  },
    ],
  },
]

// Labels for the page header breadcrumb
const routeLabels: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/clients':   'Clientes',
  '/invoices':  'Facturación',
  '/inventory': 'Inventario',
  '/employees': 'Empleados',
  '/suppliers': 'Proveedores',
  '/reports':   'Reportes',
  '/company':   'Mi Empresa',
  '/users':     'Usuarios',
  '/roles':     'Roles y permisos',
  '/audit':     'Auditoría',
}

// ── Avatar ────────────────────────────────────────────────────────────────────

function Avatar({ name, size = 'sm' }: { name?: string; size?: 'sm' | 'md' }) {
  const initials = name
    ? name
        .split(' ')
        .slice(0, 2)
        .map((n) => n[0])
        .join('')
        .toUpperCase()
    : '?'

  const sizeClass = size === 'md' ? 'w-9 h-9 text-sm' : 'w-7 h-7 text-xs'

  return (
    <div
      className={[
        sizeClass,
        'rounded-full flex items-center justify-center font-semibold shrink-0',
        'bg-gradient-to-br from-indigo-500 to-violet-600 text-white',
        'ring-2 ring-white dark:ring-zinc-900 shadow-sm',
      ].join(' ')}
    >
      {initials}
    </div>
  )
}

// ── Sidebar content ───────────────────────────────────────────────────────────

function TenantSwitcher() {
  const session      = useAuthStore((s) => s.session)
  const switchTenant = useAuthStore((s) => s.switchTenant)
  const queryClient  = useQueryClient()
  const [switching, setSwitching] = useState(false)

  if (!session?.tenant) return null
  const others = session.memberships.filter((m) => m.tenant_id !== session.tenant?.id)

  const handleSwitch = async (tenantId: number) => {
    setSwitching(true)
    try {
      await switchTenant(tenantId)
      queryClient.clear()  // ningún dato en caché de la empresa anterior
    } finally {
      setSwitching(false)
    }
  }

  return (
    <div className="px-5 pb-3">
      <p className="text-xs font-medium text-zinc-900 dark:text-zinc-100 truncate" title={session.tenant.name}>
        {session.tenant.name}
      </p>
      <p className="text-[11px] text-zinc-500 dark:text-zinc-500 truncate">{session.role?.name}</p>
      {others.length > 0 && (
        <label className="mt-2 flex items-center gap-1.5 text-[11px] text-zinc-500 dark:text-zinc-400">
          <ArrowLeftRight size={12} className="shrink-0" />
          <span className="sr-only">Cambiar de empresa</span>
          <select
            value=""
            disabled={switching}
            onChange={(e) => e.target.value && void handleSwitch(Number(e.target.value))}
            className="w-full bg-transparent text-[11px] focus:outline-none cursor-pointer"
          >
            <option value="">Cambiar de empresa…</option>
            {others.map((m) => <option key={m.tenant_id} value={m.tenant_id}>{m.tenant_name}</option>)}
          </select>
        </label>
      )}
    </div>
  )
}

function SidebarContent({ onNavClick }: { onNavClick?: () => void }) {
  const user   = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const can    = useCan()
  const hasFeature = useHasFeature()
  const { theme, toggleTheme } = useThemeStore()
  const navigate    = useNavigate()
  const queryClient = useQueryClient()

  const handleLogout = async () => {
    await logout()  // revoca el refresh token en el servidor
    queryClient.clear()
    navigate('/login')
  }

  const visibleGroups = navGroups
    .map((g) => ({
      ...g,
      items: g.items.filter((i) => (!i.permission || can(i.permission)) && (!i.feature || hasFeature(i.feature))),
    }))
    .filter((g) => g.items.length > 0)

  return (
    <div className="flex flex-col h-full">

      {/* ── Logo ── */}
      <div className="h-14 flex items-center px-5 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-sm shadow-indigo-500/30">
            <span className="text-white text-xs font-bold">G</span>
          </div>
          <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight">
            GestorPro
          </span>
        </div>
      </div>

      <TenantSwitcher />

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto px-3 pb-4 space-y-5">
        {visibleGroups.map((group) => (
          <div key={group.label}>
            <p className="px-2.5 mb-1 text-[10px] font-semibold tracking-widest uppercase text-zinc-400 dark:text-zinc-600">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={onNavClick}
                  className={({ isActive }) =>
                    [
                      'relative flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium',
                      'transition-all duration-150 group',
                      isActive
                        ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-400 nav-item-active'
                        : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800/80 dark:hover:text-zinc-100',
                    ].join(' ')
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        size={16}
                        className={[
                          'shrink-0 transition-colors',
                          isActive
                            ? 'text-indigo-600 dark:text-indigo-400'
                            : 'text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300',
                        ].join(' ')}
                      />
                      <span className="truncate">{label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* ── Bottom: user + theme toggle ── */}
      <div className="shrink-0 border-t border-zinc-200 dark:border-zinc-800 p-3 space-y-1">

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className={[
            'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium',
            'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900',
            'dark:text-zinc-400 dark:hover:bg-zinc-800/80 dark:hover:text-zinc-100',
            'transition-all duration-150',
          ].join(' ')}
        >
          {theme === 'dark' ? (
            <Sun size={16} className="text-zinc-400 shrink-0" />
          ) : (
            <Moon size={16} className="text-zinc-400 shrink-0" />
          )}
          <span>{theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}</span>
        </button>

        {/* User card */}
        <div className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800/80 transition-colors cursor-default group">
          <Avatar name={user?.full_name} size="sm" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate leading-none mb-0.5">
              {user?.full_name ?? 'Usuario'}
            </p>
            <p className="text-xs text-zinc-500 dark:text-zinc-500 truncate">
              {user?.email}
            </p>
          </div>
          <button
            onClick={() => void handleLogout()}
            title="Cerrar sesión"
            aria-label="Cerrar sesión"
            className={[
              'p-1 rounded-md transition-all',
              'text-zinc-400 hover:text-red-600 hover:bg-red-50',
              'dark:hover:text-red-400 dark:hover:bg-red-950/40',
            ].join(' ')}
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main Layout ───────────────────────────────────────────────────────────────

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const tenantName = useAuthStore((s) => s.session?.tenant?.name)

  const currentLabel = routeLabels[location.pathname] ?? 'GestorPro'

  return (
    <div className="flex h-screen bg-zinc-50 dark:bg-zinc-950 overflow-hidden transition-colors duration-300">

      {/* ── Desktop sidebar ── */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 transition-colors duration-300">
        <SidebarContent />
      </aside>

      {/* ── Mobile drawer ── */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in"
            onClick={() => setSidebarOpen(false)}
          />
          {/* Panel */}
          <aside className="animate-slide-left absolute left-0 top-0 h-full w-64 bg-white dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800 flex flex-col shadow-2xl">
            <div className="absolute top-3 right-3">
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1.5 rounded-lg text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                aria-label="Cerrar menú"
              >
                <X size={16} />
              </button>
            </div>
            <SidebarContent onNavClick={() => setSidebarOpen(false)} />
          </aside>
        </div>
      )}

      {/* ── Main content ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* ── Top header ── */}
        <header className="h-14 shrink-0 bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 flex items-center px-4 md:px-6 gap-3 transition-colors duration-300">

          {/* Mobile hamburger */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden p-1.5 rounded-lg text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label="Abrir menú"
          >
            <Menu size={18} />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-sm">
            <span className="hidden md:block text-zinc-400 dark:text-zinc-600 font-medium truncate max-w-[16rem]">{tenantName ?? 'GestorPro'}</span>
            <ChevronRight size={14} className="hidden md:block text-zinc-300 dark:text-zinc-700" />
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">{currentLabel}</span>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Right actions */}
          <div className="flex items-center gap-2">
            {/* Avatar (desktop only) */}
            <div className="hidden md:block">
              <Avatar name={user?.full_name} size="sm" />
            </div>
          </div>
        </header>

        {/* ── Page content ── */}
        <main className="flex-1 overflow-auto">
          <div className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
